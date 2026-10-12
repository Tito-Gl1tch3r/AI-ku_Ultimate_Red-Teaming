use super::server::ApiResponse;
use super::server::AuthApiResponse;
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
use base64::encode;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::fmt::format;
use std::sync::{Arc, Mutex};
use std::time::Duration;

pub async fn authenticate_user(
    creds: web::Data<Arc<Mutex<CredsManager>>>,
    payload: web::Json<UserRequest>,
) -> HttpResponse {
    let UserRequest {
        username,
        password,
        role: _,
    } = &*payload;

    if creds.lock().unwrap().authenticate(username, password) {
        let non_decode_token = format!("{}:{}", username.to_string(), password.to_string());
        let encoded_cred = non_decode_token.as_bytes();
        let token = encode(encoded_cred);
        let res_token = format!("qbx.{}", token);
        HttpResponse::Ok().json(AuthApiResponse {
            is_success: true,
            data: "Authentication successful".to_string(),
            token: Option::Some(res_token),
        })
    } else {
        HttpResponse::Ok().json(AuthApiResponse {
            is_success: false,
            data: "Authentication failed".to_string(),
            token: None,
        })
    }
}
