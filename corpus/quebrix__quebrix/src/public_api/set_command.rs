use super::server::ApiResponse;
use super::server::SetRequest;
use super::server::UserRequest;
use crate::creds::auth::Authenticator;
use crate::{
    cache::{
        cache::ResultValue, clear_cluster::ClearCluster, decr::Decr, delete::Delete, get::Get,
        get_all_clusters::GetAllClusters, get_cluster_keys::GetClusterKeys, incr::Incr, set::Set,
        set_cluster::SetCluster, Cache,
    },
    creds::cred_manager::{CredsManager, RoleManagement, User},
};
use actix_web::{
    http::header::HeaderMap, middleware::Logger, web, App, HttpRequest, HttpResponse, HttpServer,
};
use base64::decode;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::sync::{Arc, Mutex};
use std::time::Duration;
pub async fn set(
    cache: web::Data<Arc<Mutex<Cache>>>,
    creds: web::Data<Arc<Mutex<CredsManager>>>,
    payload: web::Json<SetRequest>,
    req: HttpRequest,
) -> HttpResponse {
    let SetRequest {
        cluster,
        key,
        value,
        ttl,
    } = &*payload;
    let headers: &HeaderMap = req.headers();
    
    // Handle missing Authorization header
    let auth_header = match headers.get("Authorization") {
        Some(header) => match header.to_str() {
            Ok(val) => val.to_string(),
            Err(_) => return HttpResponse::BadRequest().json(ApiResponse::fail("Invalid Authorization header format")),
        },
        None => return HttpResponse::Unauthorized().json(ApiResponse::fail("Authorization header is required")),
    };

    let qbx_token: Vec<&str> = auth_header.split(".").collect();
    let non_qbx_token = match qbx_token.get(1) {
        Some(token) => token,
        None => return HttpResponse::BadRequest().json(ApiResponse::fail("Invalid token format")),
    };

    let decoded_bytes = match decode(non_qbx_token) {
        Ok(data) => data,
        Err(_) => return HttpResponse::Unauthorized().json(ApiResponse::fail("Authentication failed")),
    };

    let decoded_credentials = match std::str::from_utf8(&decoded_bytes) {
        Ok(creds_str) => creds_str,
        Err(_) => return HttpResponse::BadRequest().json(ApiResponse::fail("Invalid token encoding")),
    };

    let creds_vec: Vec<&str> = decoded_credentials.split(":").collect();
    let username = match creds_vec.get(0) {
        Some(u) => u,
        None => return HttpResponse::BadRequest().json(ApiResponse::fail("Invalid credentials format")),
    };
    let password = match creds_vec.get(1) {
        Some(p) => p,
        None => return HttpResponse::BadRequest().json(ApiResponse::fail("Invalid credentials format")),
    };

    // Authenticate user
    let mut creds_lock = match creds.lock() {
        Ok(c) => c,
        Err(_) => return HttpResponse::InternalServerError().json(ApiResponse::fail("Internal server error")),
    };

    if !creds_lock.authenticate(username, password) {
        return HttpResponse::Unauthorized().json(ApiResponse::fail("Authentication failed"));
    }

    // Check permissions: only Admin and Developer roles can use SET
    let user = creds_lock.get_user(username);
    if !user.role.can_manage_cache() {
        return HttpResponse::Forbidden().json(ApiResponse::fail("Permission denied: Insufficient privileges to set cache values"));
    }
    // Drop creds lock before acquiring cache lock to avoid potential deadlock
    drop(creds_lock);

    let set_value = value.as_bytes();
    let ttl_duration = ttl.map(Duration::from_millis);
    let set_result = cache.lock().unwrap().set(
        cluster.clone(),
        key.clone(),
        Vec::from(set_value),
        ttl_duration,
        false,
    );

    if set_result {
        HttpResponse::Ok().json(ApiResponse::ok("Set operation successful"))
    } else {
        HttpResponse::InternalServerError().json(ApiResponse::fail("Set operation failed: memory limit exceeded"))
    }
}