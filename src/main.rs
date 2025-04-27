mod macro_runner;

use actix_web::{web, App, HttpServer, Responder, HttpResponse};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MacroStatus {
    status: String,
    pid: Option<u32>,
    log_path: Option<String>,
}

struct AppState {
    macro_status: Mutex<HashMap<String, MacroStatus>>,
}

#[derive(Debug, Deserialize)]
struct RunMacroRequest {
    yaml_path: String,
    mode: Option<String>,
}

async fn run_macro(data: web::Json<RunMacroRequest>, state: web::Data<AppState>) -> impl Responder {
    // Parse the request
    let yaml_path = &data.yaml_path;
    let mode = data.mode.clone().unwrap_or_else(|| "normal".to_string());
    
    // Call the macro runner
    match macro_runner::run_macro(yaml_path, &mode) {
        Ok(response) => {
            // Update the macro status
            let mut status_map = state.macro_status.lock().unwrap();
            status_map.insert(yaml_path.clone(), response.clone());
            
            HttpResponse::Ok().json(response)
        },
        Err(e) => {
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to run macro: {}", e)
            }))
        }
    }
}

async fn get_macro_status(path: web::Path<String>, state: web::Data<AppState>) -> impl Responder {
    let macro_id = path.into_inner();
    let status_map = state.macro_status.lock().unwrap();
    
    match status_map.get(&macro_id) {
        Some(status) => HttpResponse::Ok().json(status),
        None => HttpResponse::NotFound().json(serde_json::json!({
            "error": "Macro not found"
        }))
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    let app_state = web::Data::new(AppState {
        macro_status: Mutex::new(HashMap::new()),
    });
    
    println!("Starting BettermanAI TagUI Wrapper on http://localhost:8080");
    
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .route("/run_macro", web::post().to(run_macro))
            .route("/macro_status/{id}", web::get().to(get_macro_status))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}