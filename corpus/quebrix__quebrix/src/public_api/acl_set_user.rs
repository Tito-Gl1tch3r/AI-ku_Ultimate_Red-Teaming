use super::server::ApiResponse;
use super::server::UserRequest;
use crate::creds::acl_add_user::IAddUser;
use crate::creds::auth::Authenticator;
use crate::creds::cred_manager::ACLResult;
use crate::creds::role_manager::IRoleManager;
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
pub async fn add_user(
    creds: web::Data<Arc<Mutex<CredsManager>>>,
    payload: web::Json<UserRequest>,
    req: HttpRequest,
) -> HttpResponse {
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
    let auth_result = creds
        .lock()
        .unwrap()
        .authenticate(username, creds_vec.get(1).unwrap());
    let mut current_user: User;
    if auth_result {
        current_user = creds.lock().unwrap().get_user(username);
    } else {
        return HttpResponse::Ok().json(ApiResponse::fail("invalid pass or username"));
    }

    if !creds.lock().unwrap().is_admin(&current_user) {
        return HttpResponse::Ok().json(ApiResponse::fail(
            "Permission denied: Admin role required to add users",
        ));
    }

    let UserRequest {
        username,
        password,
        role,
    } = &*payload;

    let mut cred = creds.lock().unwrap();
    let cred_result = cred.add_user(
        username.clone(),
        password.clone(),
        role.clone().parse::<RoleManagement>().unwrap(),
        Option::Some((&current_user)),
    );
    if cred_result.is_success {
        return HttpResponse::Ok().json(ApiResponse::ok(cred_result.message));
    } else {
        return HttpResponse::Ok().json(ApiResponse::fail(cred_result.message));
    }
}
