use super::server::ApiResponse;
use super::server::MoveClusterValueRequest;
use super::server::SetRequest;
use super::server::UserRequest;
use crate::cache::move_cluster::CopyCluster;
use crate::cache::move_del_cluster::MoveCluster;
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
pub async fn move_cluster(
    cache: web::Data<Arc<Mutex<Cache>>>,
    creds: web::Data<Arc<Mutex<CredsManager>>>,
    payload: web::Json<MoveClusterValueRequest>,
    req: HttpRequest,
) -> HttpResponse {
    let MoveClusterValueRequest {
        src_cluster,
        desc_cluster,
    } = &*payload;
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

    let set_result = cache
        .lock()
        .unwrap()
        .move_cluster(&src_cluster.as_str(), &desc_cluster.as_str());
    if set_result {
        HttpResponse::Ok().json(ApiResponse::ok("cluster moved"))
    } else {
        HttpResponse::Ok().json(ApiResponse::fail("operation failed"))
    }
}
