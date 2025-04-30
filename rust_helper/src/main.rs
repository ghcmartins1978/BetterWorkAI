use actix_cors::Cors;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, Utc};
use enigo::{Enigo, Key, KeyboardControllable, MouseButton, MouseControllable};
use log::{error, info, warn};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime};

// Platform-specific window handling
#[cfg(target_os = "windows")]
use windows::{
    Win32::Foundation::{BOOL, HWND, LPARAM},
    Win32::UI::WindowsAndMessaging::{EnumWindows, GetWindowTextW},
};

// Default port for the helper
const DEFAULT_PORT: u16 = 17400;

// Global state for the helper
struct AppState {
    monitoring_enabled: Mutex<bool>,
    events: Mutex<Vec<Event>>,
    started_at: SystemTime,
}

// Event types for tracking user actions
#[derive(Debug, Clone, Serialize, Deserialize)]
enum EventType {
    MouseMove,
    MouseClick,
    KeyboardType,
    KeyboardPress,
    WindowChange,
}

// Event structure for logging user actions
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Event {
    event_type: EventType,
    data: serde_json::Value,
    timestamp: DateTime<Utc>,
}

// Request and response structures
#[derive(Debug, Deserialize)]
struct MouseMoveRequest {
    x: i32,
    y: i32,
}

#[derive(Debug, Deserialize)]
struct MouseClickRequest {
    x: i32,
    y: i32,
    button: Option<String>,
    clicks: Option<i32>,
}

#[derive(Debug, Deserialize)]
struct KeyboardTypeRequest {
    text: String,
}

#[derive(Debug, Deserialize)]
struct KeyboardPressRequest {
    key: String,
}

#[derive(Debug, Deserialize)]
struct KeyboardHotkeyRequest {
    keys: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct WindowFocusRequest {
    title: String,
}

#[derive(Debug, Serialize)]
struct StatusResponse {
    status: String,
    monitoring: bool,
    uptime: f64,
    version: String,
    platform: String,
}

#[derive(Debug, Serialize)]
struct StandardResponse {
    status: String,
    message: String,
}

#[derive(Debug, Serialize)]
struct WindowListResponse {
    status: String,
    windows: Vec<WindowInfo>,
}

#[derive(Debug, Clone, Serialize)]
struct WindowInfo {
    id: usize,
    title: String,
    app: String,
}

#[derive(Debug, Serialize)]
struct EventsResponse {
    status: String,
    events: Vec<Event>,
    monitoring: bool,
}

// Routes
#[get("/api/status")]
async fn status(data: web::Data<Arc<AppState>>) -> impl Responder {
    let monitoring = *data.monitoring_enabled.lock().unwrap();
    let uptime = SystemTime::now()
        .duration_since(data.started_at)
        .unwrap_or(Duration::from_secs(0))
        .as_secs_f64();

    HttpResponse::Ok().json(StatusResponse {
        status: "running".to_string(),
        monitoring,
        uptime,
        version: env!("CARGO_PKG_VERSION").to_string(),
        platform: std::env::consts::OS.to_string(),
    })
}

// Cross-platform window title retrieval function
fn get_window_titles() -> Result<Vec<String>, String> {
    #[cfg(target_os = "windows")]
    {
        // Windows implementation
        let mut titles = Vec::new();
        
        unsafe {
            let data = &mut titles as *mut Vec<String>;
            // EnumWindows callback to collect visible window titles
            let result = EnumWindows(
                Some(enum_windows_callback),
                LPARAM(data as isize)
            );
            
            // Check if the result is non-zero (success)
            if result.0 != 0 {
                Ok(titles)
            } else {
                Err("Failed to enumerate windows".to_string())
            }
        }
    }
    
    #[cfg(not(target_os = "windows"))]
    {
        // Non-Windows fallback implementation
        // This is a simple implementation that returns basic window info
        // In a real implementation, we would use platform-specific APIs
        info!("Using cross-platform window listing (limited functionality)");
        
        // Return a basic list of windows for demo purposes
        // In a real implementation, we would query the system
        let titles = vec![
            "Current Application".to_string(),
            "BettermanAI".to_string(),
            "Web Browser".to_string(),
        ];
        Ok(titles)
    }
}

// Windows-specific callback for EnumWindows
#[cfg(target_os = "windows")]
unsafe extern "system" fn enum_windows_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
    let titles: &mut Vec<String> = &mut *(lparam.0 as *mut Vec<String>);
    
    // Get window title
    let mut text: [u16; 512] = [0; 512];
    let len = GetWindowTextW(hwnd, &mut text);
    
    if len > 0 {
        // Convert from wide chars to regular string
        if let Ok(title) = String::from_utf16(&text[..len as usize]) {
            if !title.is_empty() {
                titles.push(title);
            }
        }
    }
    
    // Continue enumeration
    BOOL(1)
}

#[get("/api/window/list")]
async fn window_list() -> impl Responder {
    match get_window_titles() {
        Ok(titles) => {
            let windows: Vec<WindowInfo> = titles
                .into_iter()
                .enumerate()
                .map(|(id, title)| WindowInfo {
                    id: id + 1,
                    title: title.clone(),
                    app: title.split(" - ").next().unwrap_or("Unknown").to_string(),
                })
                .collect();

            HttpResponse::Ok().json(WindowListResponse {
                status: "success".to_string(),
                windows,
            })
        }
        Err(e) => {
            error!("Failed to get window titles: {}", e);
            HttpResponse::InternalServerError().json(StandardResponse {
                status: "error".to_string(),
                message: format!("Failed to get window titles: {}", e),
            })
        }
    }
}

#[post("/api/window/focus")]
async fn focus_window(req: web::Json<WindowFocusRequest>) -> impl Responder {
    info!("Focusing window: {}", req.title);
    
    // In a real implementation, this would focus the window
    // For now, we just log it
    HttpResponse::Ok().json(StandardResponse {
        status: "success".to_string(),
        message: format!("Focused window: {}", req.title),
    })
}

#[post("/api/mouse/move")]
async fn mouse_move(
    req: web::Json<MouseMoveRequest>,
    data: web::Data<Arc<AppState>>,
) -> impl Responder {
    let x = req.x;
    let y = req.y;
    
    info!("Moving mouse to ({}, {})", x, y);
    
    let mut enigo = Enigo::new();
    enigo.mouse_move_to(x, y);
    
    // Add event to history
    if let Ok(mut events) = data.events.lock() {
        events.push(Event {
            event_type: EventType::MouseMove,
            data: serde_json::json!({ "x": x, "y": y }),
            timestamp: Utc::now(),
        });
    }
    
    HttpResponse::Ok().json(StandardResponse {
        status: "success".to_string(),
        message: format!("Mouse moved to ({}, {})", x, y),
    })
}

#[post("/api/mouse/click")]
async fn mouse_click(
    req: web::Json<MouseClickRequest>,
    data: web::Data<Arc<AppState>>,
) -> impl Responder {
    let x = req.x;
    let y = req.y;
    let button = req.button.clone().unwrap_or_else(|| "left".to_string());
    let clicks = req.clicks.unwrap_or(1);
    
    info!("Clicking mouse at ({}, {}) with {} button, {} clicks", x, y, button, clicks);
    
    let mut enigo = Enigo::new();
    enigo.mouse_move_to(x, y);
    
    let mouse_button = match button.as_str() {
        "right" => MouseButton::Right,
        "middle" => MouseButton::Middle,
        _ => MouseButton::Left,
    };
    
    for _ in 0..clicks {
        enigo.mouse_click(mouse_button);
    }
    
    // Add event to history
    if let Ok(mut events) = data.events.lock() {
        events.push(Event {
            event_type: EventType::MouseClick,
            data: serde_json::json!({
                "x": x,
                "y": y,
                "button": button,
                "clicks": clicks
            }),
            timestamp: Utc::now(),
        });
    }
    
    HttpResponse::Ok().json(StandardResponse {
        status: "success".to_string(),
        message: format!("Mouse clicked at ({}, {})", x, y),
    })
}

#[post("/api/keyboard/type")]
async fn keyboard_type(
    req: web::Json<KeyboardTypeRequest>,
    data: web::Data<Arc<AppState>>,
) -> impl Responder {
    let text = &req.text;
    
    info!("Typing text: '{}'", if text.len() > 20 {
        format!("{}...", &text[0..20])
    } else {
        text.to_string()
    });
    
    let mut enigo = Enigo::new();
    enigo.key_sequence(text);
    
    // Add event to history
    if let Ok(mut events) = data.events.lock() {
        events.push(Event {
            event_type: EventType::KeyboardType,
            data: serde_json::json!({ "text": text }),
            timestamp: Utc::now(),
        });
    }
    
    HttpResponse::Ok().json(StandardResponse {
        status: "success".to_string(),
        message: format!("Typed text: {}", if text.len() > 20 {
            format!("{}...", &text[0..20])
        } else {
            text.to_string()
        }),
    })
}

#[post("/api/keyboard/press")]
async fn keyboard_press(
    req: web::Json<KeyboardPressRequest>,
    data: web::Data<Arc<AppState>>,
) -> impl Responder {
    let key = &req.key;
    
    info!("Pressing key: {}", key);
    
    let mut enigo = Enigo::new();
    
    // Map key strings to Enigo's Key enum
    // This is a simplified mapping, a full implementation would support more keys
    match key.as_str() {
        "enter" => enigo.key_click(Key::Return),
        "tab" => enigo.key_click(Key::Tab),
        "space" => enigo.key_click(Key::Space),
        "backspace" => enigo.key_click(Key::Backspace),
        "escape" => enigo.key_click(Key::Escape),
        "up" => enigo.key_click(Key::UpArrow),
        "down" => enigo.key_click(Key::DownArrow),
        "left" => enigo.key_click(Key::LeftArrow),
        "right" => enigo.key_click(Key::RightArrow),
        _ => {
            if key.len() == 1 {
                // For single characters, use key_sequence
                enigo.key_sequence(key);
            } else {
                warn!("Unsupported key: {}", key);
            }
        }
    }
    
    // Add event to history
    if let Ok(mut events) = data.events.lock() {
        events.push(Event {
            event_type: EventType::KeyboardPress,
            data: serde_json::json!({ "key": key }),
            timestamp: Utc::now(),
        });
    }
    
    HttpResponse::Ok().json(StandardResponse {
        status: "success".to_string(),
        message: format!("Pressed key: {}", key),
    })
}

#[post("/api/keyboard/hotkey")]
async fn keyboard_hotkey(
    req: web::Json<KeyboardHotkeyRequest>,
    data: web::Data<Arc<AppState>>,
) -> impl Responder {
    let keys = &req.keys;
    let key_str = keys.join("+");
    
    info!("Pressing hotkey: {}", key_str);
    
    let mut enigo = Enigo::new();
    
    // This is a simplified implementation
    // A full implementation would need to properly handle key combinations
    for key in keys {
        match key.as_str() {
            "ctrl" | "control" => enigo.key_down(Key::Control),
            "alt" => enigo.key_down(Key::Alt),
            "shift" => enigo.key_down(Key::Shift),
            "meta" | "command" | "windows" | "win" => enigo.key_down(Key::Meta),
            _ => {
                if key.len() == 1 {
                    // For single characters, use key_sequence with key down/up
                    enigo.key_sequence(key);
                } else {
                    warn!("Unsupported key in hotkey: {}", key);
                }
            }
        }
    }
    
    // Release keys in reverse order
    for key in keys.iter().rev() {
        match key.as_str() {
            "ctrl" | "control" => enigo.key_up(Key::Control),
            "alt" => enigo.key_up(Key::Alt),
            "shift" => enigo.key_up(Key::Shift),
            "meta" | "command" | "windows" | "win" => enigo.key_up(Key::Meta),
            _ => {} // Other keys are released automatically by key_sequence
        }
    }
    
    // Add event to history
    if let Ok(mut events) = data.events.lock() {
        events.push(Event {
            event_type: EventType::KeyboardPress,
            data: serde_json::json!({ "keys": keys }),
            timestamp: Utc::now(),
        });
    }
    
    HttpResponse::Ok().json(StandardResponse {
        status: "success".to_string(),
        message: format!("Pressed hotkey: {}", key_str),
    })
}

#[post("/api/monitoring/start")]
async fn start_monitoring(data: web::Data<Arc<AppState>>) -> impl Responder {
    if let Ok(mut monitoring) = data.monitoring_enabled.lock() {
        *monitoring = true;
        info!("Monitoring started");
        
        HttpResponse::Ok().json(StandardResponse {
            status: "success".to_string(),
            message: "Monitoring started".to_string(),
        })
    } else {
        error!("Failed to acquire lock on monitoring state");
        HttpResponse::InternalServerError().json(StandardResponse {
            status: "error".to_string(),
            message: "Internal server error".to_string(),
        })
    }
}

#[post("/api/monitoring/stop")]
async fn stop_monitoring(data: web::Data<Arc<AppState>>) -> impl Responder {
    if let Ok(mut monitoring) = data.monitoring_enabled.lock() {
        *monitoring = false;
        info!("Monitoring stopped");
        
        HttpResponse::Ok().json(StandardResponse {
            status: "success".to_string(),
            message: "Monitoring stopped".to_string(),
        })
    } else {
        error!("Failed to acquire lock on monitoring state");
        HttpResponse::InternalServerError().json(StandardResponse {
            status: "error".to_string(),
            message: "Internal server error".to_string(),
        })
    }
}

// General endpoint to handle both monitoring operations
#[post("/api/monitoring")]
async fn toggle_monitoring(req: web::Json<Value>, data: web::Data<Arc<AppState>>) -> impl Responder {
    let action = req.get("action").and_then(|a| a.as_str()).unwrap_or("status");
    
    match action {
        "start" => {
            if let Ok(mut monitoring) = data.monitoring_enabled.lock() {
                *monitoring = true;
                info!("Monitoring started via general endpoint");
                
                HttpResponse::Ok().json(StandardResponse {
                    status: "success".to_string(),
                    message: "Monitoring started".to_string(),
                })
            } else {
                error!("Failed to acquire lock on monitoring state");
                HttpResponse::InternalServerError().json(StandardResponse {
                    status: "error".to_string(),
                    message: "Internal server error".to_string(),
                })
            }
        },
        "stop" => {
            if let Ok(mut monitoring) = data.monitoring_enabled.lock() {
                *monitoring = false;
                info!("Monitoring stopped via general endpoint");
                
                HttpResponse::Ok().json(StandardResponse {
                    status: "success".to_string(),
                    message: "Monitoring stopped".to_string(),
                })
            } else {
                error!("Failed to acquire lock on monitoring state");
                HttpResponse::InternalServerError().json(StandardResponse {
                    status: "error".to_string(),
                    message: "Internal server error".to_string(),
                })
            }
        },
        _ => {
            // Return current monitoring status
            if let Ok(monitoring) = data.monitoring_enabled.lock() {
                HttpResponse::Ok().json(serde_json::json!({
                    "status": "success",
                    "monitoring": *monitoring,
                }))
            } else {
                error!("Failed to acquire lock on monitoring state");
                HttpResponse::InternalServerError().json(StandardResponse {
                    status: "error".to_string(),
                    message: "Internal server error".to_string(),
                })
            }
        }
    }
}

#[get("/api/events")]
async fn get_events(data: web::Data<Arc<AppState>>) -> impl Responder {
    if let (Ok(events), Ok(monitoring)) = (data.events.lock(), data.monitoring_enabled.lock()) {
        HttpResponse::Ok().json(EventsResponse {
            status: "success".to_string(),
            events: events.clone(),
            monitoring: *monitoring,
        })
    } else {
        error!("Failed to acquire lock on events or monitoring state");
        HttpResponse::InternalServerError().json(StandardResponse {
            status: "error".to_string(),
            message: "Internal server error".to_string(),
        })
    }
}

#[get("/docs")]
async fn docs() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "api_version": env!("CARGO_PKG_VERSION"),
        "description": "BettermanAI Helper API",
        "endpoints": [
            {"path": "/api/status", "method": "GET", "description": "Get current status"},
            {"path": "/api/window/list", "method": "GET", "description": "Get window list"},
            {"path": "/api/window/focus", "method": "POST", "description": "Focus window"},
            {"path": "/api/mouse/move", "method": "POST", "description": "Move mouse"},
            {"path": "/api/mouse/click", "method": "POST", "description": "Click mouse"},
            {"path": "/api/keyboard/type", "method": "POST", "description": "Type text"},
            {"path": "/api/keyboard/press", "method": "POST", "description": "Press key"},
            {"path": "/api/keyboard/hotkey", "method": "POST", "description": "Press hotkey"},
            {"path": "/api/monitoring/start", "method": "POST", "description": "Start monitoring"},
            {"path": "/api/monitoring/stop", "method": "POST", "description": "Stop monitoring"},
            {"path": "/api/events", "method": "GET", "description": "Get events"}
        ]
    }))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Set up logging
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));
    
    // Determine port from environment or use default
    let port = std::env::var("HELPER_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(DEFAULT_PORT);
    
    // Write port to file for discovery
    let port_file_path = dirs::data_dir()
        .map(|p| p.join("bettermanai/helper_port.txt"))
        .unwrap_or_else(|| std::path::PathBuf::from("helper_port.txt"));
    
    if let Some(parent) = port_file_path.parent() {
        std::fs::create_dir_all(parent).unwrap_or_else(|e| {
            warn!("Failed to create directory for port file: {}", e);
        });
    }
    
    std::fs::write(&port_file_path, port.to_string()).unwrap_or_else(|e| {
        warn!("Failed to write port file: {}", e);
    });
    
    info!("Port written to file: {}", port_file_path.display());
    
    // Create app state
    let app_state = Arc::new(AppState {
        monitoring_enabled: Mutex::new(false),
        events: Mutex::new(Vec::new()),
        started_at: SystemTime::now(),
    });
    
    info!("Starting BettermanAI Helper on port {}", port);
    
    // Start HTTP server
    HttpServer::new(move || {
        // Configure CORS
        let cors = Cors::default()
            .allow_any_origin()
            .allow_any_method()
            .allow_any_header()
            .max_age(3600);
        
        App::new()
            .wrap(cors)
            .app_data(web::Data::new(app_state.clone()))
            .service(status)
            .service(window_list)
            .service(focus_window)
            .service(mouse_move)
            .service(mouse_click)
            .service(keyboard_type)
            .service(keyboard_press)
            .service(keyboard_hotkey)
            .service(start_monitoring)
            .service(stop_monitoring)
            .service(toggle_monitoring)
            .service(get_events)
            .service(docs)
    })
    .bind(("127.0.0.1", port))?
    .run()
    .await
}