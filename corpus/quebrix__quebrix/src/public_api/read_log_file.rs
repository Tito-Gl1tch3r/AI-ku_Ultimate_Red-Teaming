use super::server::ApiResponse;
use super::server::SetRequest;
use super::server::UserRequest;
use crate::creds::auth::Authenticator;
use crate::creds::cred_users::CredUsers;
use crate::creds::who_am_i::WhowAmI;
use crate::logger::logger_manager::Logger;
use crate::{
    cache::{
        cache::ResultValue, clear_cluster::ClearCluster, decr::Decr, delete::Delete, get::Get,
        get_all_clusters::GetAllClusters, get_cluster_keys::GetClusterKeys, incr::Incr, set::Set,
        set_cluster::SetCluster, Cache,
    },
    creds::cred_manager::{CredsManager, RoleManagement, User},
};
use actix_web::{http::header::HeaderMap, web, App, HttpRequest, HttpResponse, HttpServer};
use base64::decode;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::sync::{Arc, Mutex};
use std::time::Duration;

pub async fn load_logs(
    creds: web::Data<Arc<Mutex<CredsManager>>>,
    req: HttpRequest,
) -> HttpResponse {
    let auth_header = match req.headers().get("Authorization") {
        Some(header) => header.to_str().unwrap_or(""),
        None => {
            return HttpResponse::BadRequest()
                .json(ApiResponse::fail("Authorization header missing"))
        }
    };

    let decoded_bytes = match decode(auth_header) {
        Ok(bytes) => bytes,
        Err(_) => {
            return HttpResponse::BadRequest()
                .json(ApiResponse::fail("Failed to decode Base64 string"))
        }
    };

    let decoded_credentials = match std::str::from_utf8(&decoded_bytes) {
        Ok(credentials) => credentials,
        Err(_) => {
            return HttpResponse::BadRequest()
                .json(ApiResponse::fail("Failed to convert credentials to string"))
        }
    };

    let creds_vec: Vec<&str> = decoded_credentials.split(':').collect();
    if creds_vec.len() != 2 {
        return HttpResponse::BadRequest().json(ApiResponse::fail("Invalid credentials format"));
    }

    let username = creds_vec[0];
    let password = creds_vec[1];

    if !creds.lock().unwrap().authenticate(username, password) {
        return HttpResponse::Unauthorized().json(ApiResponse::fail("Authentication failed"));
    }

    let logs = Logger::return_logs();
    if logs.is_empty() {
        HttpResponse::Ok().json(ApiResponse::ok("nothing to log"))
    } else {
        HttpResponse::Ok().json(ApiResponse::ok(logs))
    }
}
