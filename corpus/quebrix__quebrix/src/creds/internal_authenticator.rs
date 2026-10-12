use actix_web::{http::header::HeaderMap, HttpResponse};
use base64::decode;

use crate::public_api::server::ApiResponse;

use super::cred_manager::{self, CredsManager};

pub trait InternalAuthenticator {
    fn authenticate_internal<'a>(
        &self,
        header: &'a HeaderMap,
    ) -> (Option<HttpResponse>, Option<&'a str>);
}

impl InternalAuthenticator for CredsManager {
    fn authenticate_internal<'a>(
        &self,
        header: &'a HeaderMap,
    ) -> (Option<HttpResponse>, Option<&'a str>) {
        let auth = header.get("Authorization").unwrap().to_str().unwrap();
        let decr_auth = match decode(auth.clone()) {
            Ok(decrypet_data) => Some(decrypet_data),
            Err(_) => None,
        };
        if decr_auth.is_none() {
            return (
                Option::Some(
                    HttpResponse::Unauthorized().json(ApiResponse::fail("Authentication failed")),
                ),
                Option::None,
            );
        } else {
            (None, Option::Some(auth))
        }
    }
}
