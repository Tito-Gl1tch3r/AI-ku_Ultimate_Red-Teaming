use super::server::ApiResponse;
use super::server::UserRequest;
use crate::{
    cache::{
        cache::ResultValue, clear_cluster::ClearCluster, decr::Decr, delete::Delete, get::Get,
        get_all_clusters::GetAllClusters, get_cluster_keys::GetClusterKeys, incr::Incr, set::Set,
        set_cluster::SetCluster, Cache,
    },
    creds::{
        auth::Authenticator,
        cred_manager::{CredsManager, RoleManagement, User},
    },
};
use actix_web::{
    http::header::HeaderMap, middleware::Logger, web, App, HttpRequest, HttpResponse, HttpServer,
};
use base64::decode;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::sync::{Arc, Mutex};
use std::time::Duration;
pub async fn get_all_clusters(
    cache: web::Data<Arc<Mutex<Cache>>>,
    creds: web::Data<Arc<Mutex<CredsManager>>>,
    req: HttpRequest,
) -> HttpResponse {
    let clusters = cache.lock().unwrap().get_all_clusters();
    let headers: &HeaderMap = req.headers();
    let auth = headers.get("Authorization").unwrap().to_str().unwrap();
    let qbx_token: Vec<&str> = auth.split(".").collect();
    let non_qbx_token = qbx_token.get(1).unwrap();
    let decr_auth = match decode(non_qbx_token) {
        Ok(decrypet_data) => Some(decrypet_data),
        Err(_) => None,
    };

    if decr_auth.is_none() {
        return HttpResponse::Unauthorized().json(ApiResponse::fail("Authentication failed"));
    }
    let decoded_bytes = decode(non_qbx_token).expect("Failed to decode Base64 string");
    let decoded_credentials =
        std::str::from_utf8(&decoded_bytes).expect("Failed to convert bytes to string");
    let creds_vec: Vec<&str> = decoded_credentials.split(":").collect();
    let username = creds_vec.get(0).unwrap();
    let password = creds_vec.get(1).unwrap();

    if !creds.lock().unwrap().authenticate(username, password) {
        return HttpResponse::Unauthorized().json(ApiResponse::fail("Authentication failed"));
    }
    if !clusters.is_empty() {
        HttpResponse::Ok().json(ApiResponse::ok(clusters))
    } else {
        HttpResponse::Ok().json(ApiResponse::fail("No clusters found on this port"))
    }
}
