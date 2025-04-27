import logging
import json
import time
import threading
from datetime import datetime, timedelta

from database import db_session
from models import ScheduledJob, EventSequence, Pattern
from ai_analysis_script import analyze_pattern_with_openai, store_analysis_in_database

logger = logging.getLogger(__name__)

class JobScheduler:
    """
    Manages and runs scheduled jobs
    """
    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.scheduler_thread = None
        self.check_interval = 60  # Check for jobs every minute
        self.job_executors = {
            'rolling_pattern_detection': RollingPatternDetectionJob(),
            'nightly_pattern_analysis': NightlyPatternAnalysisJob()
        }
        
    def start(self):
        """Start the job scheduler"""
        if self.running:
            return
            
        logger.info("Starting job scheduler")
        self.running = True
        
        # Initialize default scheduled jobs if needed
        self._init_default_jobs()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
    def stop(self):
        """Stop the job scheduler"""
        logger.info("Stopping job scheduler")
        self.running = False
        
    def _init_default_jobs(self):
        """Initialize default scheduled jobs if none exist"""
        try:
            # Check if jobs exist
            jobs = db_session.query(ScheduledJob).all()
            
            if not jobs:
                logger.info("Creating default scheduled jobs")
                
                # Get settings
                jobs_enabled = self.settings.get_setting('jobs_enabled', True)
                rolling_interval = self.settings.get_setting('rolling_pattern_detection_interval', 240)
                rolling_window = self.settings.get_setting('rolling_pattern_detection_time_window', 2)
                nightly_time_str = self.settings.get_setting('nightly_pattern_analysis_time', '03:00')
                nightly_window = self.settings.get_setting('nightly_pattern_analysis_time_window', 7)
                nightly_min_score = self.settings.get_setting('nightly_pattern_analysis_min_score', 0.7)
                
                # Create rolling pattern detection job
                rolling_job = ScheduledJob(
                    job_type='rolling_pattern_detection',
                    next_run_time=datetime.now() + timedelta(minutes=rolling_interval),
                    interval_minutes=rolling_interval,
                    enabled=1 if jobs_enabled else 0,
                    parameters=json.dumps({
                        'time_window_days': rolling_window,
                        'max_sequences': 100  # Maximum number of sequences to process
                    })
                )
                db_session.add(rolling_job)
                
                # Create nightly pattern analysis job (runs at specified time)
                # Parse time string (HH:MM)
                try:
                    hour, minute = map(int, nightly_time_str.split(':'))
                except (ValueError, AttributeError):
                    hour, minute = 3, 0  # Default to 3 AM
                
                # Calculate next run time
                now = datetime.now()
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run < now:
                    next_run += timedelta(days=1)
                    
                nightly_job = ScheduledJob(
                    job_type='nightly_pattern_analysis',
                    next_run_time=next_run,
                    interval_minutes=1440,  # 24 hours
                    enabled=1 if jobs_enabled else 0,
                    parameters=json.dumps({
                        'time_window_days': nightly_window,
                        'min_pattern_score': nightly_min_score
                    })
                )
                db_session.add(nightly_job)
                
                db_session.commit()
                logger.info("Default scheduled jobs created")
        except Exception as e:
            logger.error(f"Error initializing default jobs: {e}")
            db_session.rollback()
            
    def _scheduler_loop(self):
        """Thread function to check for and run scheduled jobs"""
        while self.running:
            try:
                # Get all enabled jobs that are due to run
                now = datetime.now()
                due_jobs = db_session.query(ScheduledJob).filter(
                    ScheduledJob.enabled == 1,
                    ScheduledJob.next_run_time <= now,
                    ScheduledJob.status.in_(['scheduled', 'completed', 'failed'])
                ).all()
                
                for job in due_jobs:
                    # Run job in a separate thread
                    self._run_job(job)
                    
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                
            # Sleep until next check
            time.sleep(self.check_interval)
            
    def _run_job(self, job):
        """Run a scheduled job"""
        try:
            # Mark job as running
            job.status = 'running'
            job.last_run_time = datetime.now()
            db_session.commit()
            
            # Run the job
            executor = self.job_executors.get(job.job_type)
            
            if executor:
                job_parameters = json.loads(job.parameters)
                result = executor.execute(job_parameters)
                
                # Update job with results
                job.result = json.dumps(result)
                job.status = 'completed'
            else:
                job.result = json.dumps({'error': f"No executor found for job type {job.job_type}"})
                job.status = 'failed'
                
            # Schedule next run
            job.next_run_time = datetime.now() + timedelta(minutes=job.interval_minutes)
            db_session.commit()
            
            logger.info(f"Job {job.id} ({job.job_type}) completed. Next run: {job.next_run_time}")
            
        except Exception as e:
            logger.error(f"Error running job {job.id} ({job.job_type}): {e}")
            
            try:
                # Mark job as failed
                job.status = 'failed'
                job.result = json.dumps({'error': str(e)})
                job.next_run_time = datetime.now() + timedelta(minutes=job.interval_minutes)
                db_session.commit()
            except Exception as commit_error:
                logger.error(f"Error updating job status: {commit_error}")
                db_session.rollback()


class RollingPatternDetectionJob:
    """Job for detecting patterns in recent sequences"""
    
    def execute(self, parameters):
        """
        Execute the rolling pattern detection job
        
        Args:
            parameters: Dictionary of job parameters
            
        Returns:
            Dictionary of job results
        """
        logger.info(f"Starting rolling pattern detection job with parameters: {parameters}")
        start_time = datetime.now()
        
        time_window_days = parameters.get('time_window_days', 2)
        max_sequences = parameters.get('max_sequences', 100)
        
        # Get sequences from time window
        time_threshold = datetime.now() - timedelta(days=time_window_days)
        
        try:
            # Get sequences from the specified time window
            sequences = db_session.query(EventSequence).filter(
                EventSequence.start_time > time_threshold
            ).order_by(EventSequence.start_time.desc()).limit(max_sequences).all()
            
            logger.info(f"Found {len(sequences)} sequences in the last {time_window_days} days")
            
            if len(sequences) < 2:
                return {
                    'status': 'skipped', 
                    'reason': 'Not enough sequences',
                    'sequences_found': len(sequences)
                }
                
            # Group sequences by similarity
            clusters = self._group_sequences_by_similarity(sequences)
            
            # Process clusters and create patterns
            patterns_created = self._create_patterns_from_clusters(clusters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'execution_time': execution_time,
                'sequences_analyzed': len(sequences),
                'clusters_found': len(clusters),
                'patterns_created': patterns_created
            }
            
        except Exception as e:
            logger.error(f"Error in rolling pattern detection: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _group_sequences_by_similarity(self, sequences):
        """Group sequences into clusters based on similarity"""
        clusters = []
        
        for i, seq1 in enumerate(sequences):
            # Skip if already in a cluster
            if any(seq1.id in [s.id for s in cluster] for cluster in clusters):
                continue
                
            # Start a new cluster
            current_cluster = [seq1]
            seq1_events = json.loads(seq1.data)
            
            # Compare with remaining sequences
            for j in range(i+1, len(sequences)):
                seq2 = sequences[j]
                
                # Skip if already in a cluster
                if any(seq2.id in [s.id for s in cluster] for cluster in clusters):
                    continue
                    
                try:
                    seq2_events = json.loads(seq2.data)
                    similarity = self._calculate_sequence_similarity(seq1_events, seq2_events)
                    
                    if similarity > 0.7:  # Similarity threshold
                        current_cluster.append(seq2)
                        
                except Exception as e:
                    logger.error(f"Error comparing sequences {seq1.id} and {seq2.id}: {e}")
                    
            # Add cluster if it has multiple sequences
            if len(current_cluster) > 1:
                clusters.append(current_cluster)
                
        return clusters
        
    def _calculate_sequence_similarity(self, events1, events2):
        """Calculate similarity between two event sequences"""
        import difflib
        
        # Extract event types sequences
        types1 = [e['type'] for e in events1]
        types2 = [e['type'] for e in events2]
        
        # Calculate type sequence similarity
        type_sim = difflib.SequenceMatcher(None, types1, types2).ratio()
        
        # Extract windows
        windows1 = []
        windows2 = []
        
        for e in events1:
            if 'window' in e and e['window'] and e['window'] not in windows1:
                windows1.append(e['window'])
                
        for e in events2:
            if 'window' in e and e['window'] and e['window'] not in windows2:
                windows2.append(e['window'])
                
        # Calculate window similarity
        if windows1 and windows2:
            common_windows = set(windows1).intersection(set(windows2))
            window_sim = len(common_windows) / max(len(windows1), len(windows2))
        else:
            window_sim = 0
            
        # Calculate length similarity
        len_sim = min(len(events1), len(events2)) / max(len(events1), len(events2))
        
        # Calculate weighted similarity
        similarity = (type_sim * 0.5) + (window_sim * 0.3) + (len_sim * 0.2)
        
        return similarity
        
    def _create_patterns_from_clusters(self, clusters):
        """Create patterns from sequence clusters"""
        patterns_created = 0
        
        for i, cluster in enumerate(clusters):
            try:
                # Check if this pattern already exists
                sequence_ids = [seq.id for seq in cluster]
                
                # Create a name and description
                name = f"Rolling Pattern {datetime.now().strftime('%Y%m%d-%H%M')}-{i+1}"
                description = f"Pattern detected across {len(cluster)} similar sequences"
                
                # Create pattern
                pattern = Pattern(
                    name=name,
                    description=description,
                    sequence_ids=json.dumps(sequence_ids),
                    detection_time=datetime.now(),
                    last_match_time=datetime.now(),
                    score=max(0.7, min(1.0, len(cluster) / 10.0)),  # Score based on cluster size
                    status="detected"
                )
                
                db_session.add(pattern)
                db_session.commit()
                patterns_created += 1
                
                logger.info(f"Created pattern {pattern.id} with {len(cluster)} sequences")
                
            except Exception as e:
                logger.error(f"Error creating pattern for cluster {i}: {e}")
                db_session.rollback()
                
        return patterns_created


class NightlyPatternAnalysisJob:
    """Job for deep analysis of patterns using AI"""
    
    def execute(self, parameters):
        """
        Execute the nightly pattern analysis job
        
        Args:
            parameters: Dictionary of job parameters
            
        Returns:
            Dictionary of job results
        """
        logger.info(f"Starting nightly pattern analysis job with parameters: {parameters}")
        start_time = datetime.now()
        
        time_window_days = parameters.get('time_window_days', 7)
        min_pattern_score = parameters.get('min_pattern_score', 0.7)
        
        # Get patterns from time window
        time_threshold = datetime.now() - timedelta(days=time_window_days)
        
        try:
            # Get patterns from the specified time window
            patterns = db_session.query(Pattern).filter(
                Pattern.detection_time > time_threshold,
                Pattern.score >= min_pattern_score,
                Pattern.status.in_(['detected', 'evaluated'])  # Only analyze detected or previously evaluated patterns
            ).all()
            
            logger.info(f"Found {len(patterns)} qualifying patterns in the last {time_window_days} days")
            
            if not patterns:
                return {
                    'status': 'skipped', 
                    'reason': 'No qualifying patterns',
                    'patterns_found': 0
                }
                
            # Analyze patterns with AI
            analysis_results = self._analyze_patterns(patterns)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'execution_time': execution_time,
                'patterns_analyzed': len(patterns),
                'patterns_with_analysis': len(analysis_results),
                'analysis_results': analysis_results
            }
            
        except Exception as e:
            logger.error(f"Error in nightly pattern analysis: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def _analyze_patterns(self, patterns):
        """Analyze patterns using AI"""
        analysis_results = []
        
        for pattern in patterns:
            try:
                # Get sequence IDs
                sequence_ids = json.loads(pattern.sequence_ids)
                
                if not sequence_ids or len(sequence_ids) < 2:
                    continue
                    
                # Get sequences
                sequences = db_session.query(EventSequence).filter(
                    EventSequence.id.in_(sequence_ids)
                ).all()
                
                if not sequences or len(sequences) < 2:
                    continue
                    
                # Prepare data for AI analysis
                pattern_data = {
                    'id': pattern.id,
                    'name': pattern.name,
                    'description': pattern.description,
                    'score': pattern.score,
                    'sequence_count': len(sequences)
                }
                
                sequences_data = []
                for seq in sequences:
                    try:
                        seq_data = json.loads(seq.data)
                        seq_meta = json.loads(seq.meta_data) if seq.meta_data else {}
                        
                        sequences_data.append({
                            'id': seq.id,
                            'start_time': seq.start_time.isoformat(),
                            'end_time': seq.end_time.isoformat(),
                            'event_count': seq.event_count,
                            'meta_data': seq_meta,
                            'events': seq_data[:10]  # Include only first 10 events to avoid too much data
                        })
                    except Exception as e:
                        logger.error(f"Error preparing sequence {seq.id} data: {e}")
                
                # Analyze with OpenAI
                try:
                    analysis_data = analyze_pattern_with_openai(pattern_data, sequences_data)
                    
                    # Store analysis results
                    store_analysis_in_database(pattern.id, analysis_data)
                    
                    # Update pattern status
                    pattern.status = 'evaluated'
                    if 'evaluation_notes' in analysis_data:
                        pattern.evaluation_notes = analysis_data['evaluation_notes']
                    db_session.commit()
                    
                    analysis_results.append({
                        'pattern_id': pattern.id,
                        'success': True,
                        'automation_potential': analysis_data.get('automation_potential', 0)
                    })
                except Exception as e:
                    logger.error(f"Error analyzing pattern {pattern.id} with OpenAI: {e}")
                    analysis_results.append({
                        'pattern_id': pattern.id,
                        'success': False,
                        'error': str(e)
                    })
                    
            except Exception as e:
                logger.error(f"Error processing pattern {pattern.id}: {e}")
                analysis_results.append({
                    'pattern_id': pattern.id,
                    'success': False,
                    'error': str(e)
                })
                
        return analysis_results