// pinkerton test file - performance and detection coverage
//
// expected detections:
//   amazon aws access key id     : AKIAIOSFODNN7EXAMPLE
//   google api key               : AIzaSyBabcdefghijklmnopqrstuvwxyz012345
//   github personal access token : ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ
//   github app token             : ghs_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ
//   gitlab personal access token : glpat-abcdefghijklmnopqrst
//   jwt token                    : eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
//   stripe api key               : sk_live_aBcDeFgHiJkLmNoPqRsTuVwX
//   picatic api key              : sk_live_abcdefghijklmnopqrstuvwxyz012345
//   slack oauth v2 bot token     : xoxb-12345678901-12345678901-abcdefghijklmnopqrstuvwx
//   slack webhook                : https://hooks.slack.com/services/TABCDE123/BABCDE123/abcdefghijklmnopqrstuvwx
//   mailgun api key              : key-abcdefghijklmnopqrstuvwxyz012345
//   twilio api key               : SKaAbBcCdDeEfF0123456789aAbBcCdDeE
//   shopify access token         : shpat_abcdef0123456789abcdef0123456789
//   npm access token             : npm_abcdefghijklmnopqrstuvwxyz0123456789
//   authorization bearer         : Bearer eyJhbGciOiJSUzI1NiJ9...
//   firebase url                 : myapp-default-rtdb.firebaseio.com
//   rsa private key              : -----BEGIN RSA PRIVATE KEY-----
//   doppler api token            : dp.pt.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ
//
// not expected (false positive checks):
//   api_key value too short      : api_key:"shortval" (8 chars, below 32 minimum)
//   incomplete jwt (2 parts)     : eyJhbGci.eyJzdWIi (no third segment)
//   wrong aws key prefix         : BKIAIOSFODNN7EXAMPLE
//   unrelated base64 string      : YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo=

!function(e,t,n){"use strict";var r=Object.defineProperty,i=Object.getOwnPropertyNames,o=Object.prototype.hasOwnProperty,a=function(e,t){for(var n in t)r(e,n,{get:t[n],enumerable:!0})},s=function(e,t,n){if(t&&"object"==typeof t||"function"==typeof t)for(var o of i(t))e.hasOwnProperty(o)||o===n||r(e,o,{get:()=>t[o],enumerable:!0});return e};var u={};a(u,{default:()=>c});module.exports=s(u,e);var c={version:"2.4.1",env:"production"};t.exports=n}({},{},{});

var AppConfig=function(){return{firebase:{apiKey:"AIzaSyBabcdefghijklmnopqrstuvwxyz012345",authDomain:"myapp.firebaseapp.com",databaseURL:"https://myapp-default-rtdb.firebaseio.com",projectId:"myapp-prod",storageBucket:"myapp-prod.appspot.com",messagingSenderId:"1234567890",appId:"1:1234567890:web:abcdef1234567890abcdef"},aws:{accessKeyId:"AKIAIOSFODNN7EXAMPLE",secretAccessKey:"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",region:"us-east-1",bucket:"myapp-uploads-prod"},stripe:{publishableKey:"pk_live_abcdefghijklmnopqrstuvwx",secretKey:"sk_live_aBcDeFgHiJkLmNoPqRsTuVwX"},picatic:{apiKey:"sk_live_abcdefghijklmnopqrstuvwxyz012345"},slack:{botToken:"xoxb-12345678901-12345678901-abcdefghijklmnopqrstuvwx",webhookUrl:"https://hooks.slack.com/services/TABCDE123/BABCDE123/abcdefghijklmnopqrstuvwx"},github:{personalToken:"ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ",appToken:"ghs_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"},gitlab:{pat:"glpat-abcdefghijklmnopqrst"},doppler:{token:"dp.pt.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ"},mailgun:{apiKey:"key-abcdefghijklmnopqrstuvwxyz012345"},twilio:{apiKey:"SKaAbBcCdDeEfF0123456789aAbBcCdDeE",accountSid:"ACabcdefghijklmnopqrstuvwxyz012345"},shopify:{accessToken:"shpat_abcdef0123456789abcdef0123456789"},npm:{token:"npm_abcdefghijklmnopqrstuvwxyz0123456789"}}}();

function initAuth(){var e="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";return fetch("/api/user",{method:"GET",headers:{Authorization:"Bearer eyJhbGciOiJSUzI1NiJ9.eyJ1c2VySWQiOiI5ODc2NTQzMjEifQ.dummysignaturevalue","Content-Type":"application/json"}})}

var rsaKeyHeader="-----BEGIN RSA PRIVATE KEY-----",rsaKeyFooter="-----END RSA PRIVATE KEY-----",pemContent=rsaKeyHeader+"\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4sAAAAAAAAAAAAAAAAAAAAAAAAA\n"+rsaKeyFooter;

var analytics={api_key:"shortval",app_id:"abc123",tracking_id:"UA-000000-1",debug:!1};var malformedJwt="eyJhbGci.eyJzdWIi";var wrongAwsPrefix="BKIAIOSFODNN7EXAMPLE";var unrelatedBase64="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo=";

!function(){function e(e,t){return Object.prototype.hasOwnProperty.call(e,t)}function t(e){return null!==e&&"object"==typeof e}function n(e,t){if(e===t)return!0;if(!t(e)||!t(t))return!1;var n=Object.keys(e),r=Object.keys(t);if(n.length!==r.length)return!1;for(var i=0;i<n.length;i++)if(!e(n[i],t)||!n(e[n[i]],t[n[i]]))return!1;return!0}var r={state:{user:null,token:null,isAuthenticated:!1,permissions:[],preferences:{theme:"light",language:"en",notifications:!0}},getters:{isAuthenticated:function(e){return e.isAuthenticated},currentUser:function(e){return e.user},userToken:function(e){return e.token},hasPermission:function(e){return function(t){return e.permissions.includes(t)}}},mutations:{SET_USER:function(e,t){e.user=t},SET_TOKEN:function(e,t){e.token=t},SET_AUTH:function(e,t){e.isAuthenticated=t},SET_PERMISSIONS:function(e,t){e.permissions=t},UPDATE_PREFERENCE:function(e,t){var n=t.key,r=t.value;e.preferences[n]=r}},actions:{login:async function(e,t){var n=e.commit;try{var r=await fetch("/api/v1/auth/login",{method:"POST",headers:{"Content-Type":"application/json","X-Api-Version":"2024-01"},body:JSON.stringify(t)});if(!r.ok){var i=await r.json();throw new Error(i.message||"Login failed")}var o=await r.json();n("SET_TOKEN",o.token);n("SET_USER",o.user);n("SET_PERMISSIONS",o.permissions||[]);n("SET_AUTH",!0);return o}catch(e){n("SET_AUTH",!1);throw e}},logout:function(e){var t=e.commit;t("SET_TOKEN",null);t("SET_USER",null);t("SET_PERMISSIONS",[]);t("SET_AUTH",!1);fetch("/api/v1/auth/logout",{method:"POST"}).catch(function(){})},refreshToken:async function(e){var t=e.commit,n=e.state;if(!n.token)return;try{var r=await fetch("/api/v1/auth/refresh",{method:"POST",headers:{Authorization:"Bearer "+n.token,"Content-Type":"application/json"}});if(!r.ok)throw new Error("Token refresh failed");var i=await r.json();t("SET_TOKEN",i.token)}catch(e){t("SET_TOKEN",null);t("SET_AUTH",!1)}},fetchUserProfile:async function(e){var t=e.commit,n=e.state;if(!n.token)return;var r=await fetch("/api/v1/user/me",{headers:{Authorization:"Bearer "+n.token}});if(!r.ok)throw new Error("Failed to fetch profile");var i=await r.json();t("SET_USER",i)}}};return r}();

!function(e){function t(t){var n=e.state[t];if(void 0===n)throw new Error("Unknown module: "+t);return n}function n(e,t,n){return Object.assign({},e,{[t]:n})}var r={modules:{},install:function(e){e.prototype.$store=this},registerModule:function(e,t){this.modules[e]=t},getModule:function(e){return t(e)},dispatch:async function(e,t){var n=e.split("/"),r=1===n.length?this:this.getModule(n[0]),i=1===n.length?n[0]:n[1];if(!r||!r.actions||!r.actions[i])throw new Error("Action not found: "+e);return await r.actions[i]({commit:this.commit.bind(this),state:this.state,getters:this.getters},t)},commit:function(e,t){var n=e.split("/"),r=1===n.length?this:this.getModule(n[0]),i=1===n.length?n[0]:n[1];if(!r||!r.mutations||!r.mutations[i])throw new Error("Mutation not found: "+e);r.mutations[i](r.state,t)}};return r}({});

var Router=function(){function e(e){this.routes=e.routes||[];this.history=[];this.currentRoute=null;this.beforeEachHooks=[];this.afterEachHooks=[]}e.prototype.beforeEach=function(e){this.beforeEachHooks.push(e)};e.prototype.afterEach=function(e){this.afterEachHooks.push(e)};e.prototype.push=function(e){var t=this;"string"==typeof e&&(e={path:e});var n=this.routes.find(function(t){return t.path===e.path});if(!n)return Promise.reject(new Error("Route not found: "+e.path));var r=this.currentRoute;return new Promise(function(e,i){var o=0;function a(){if(o>=t.beforeEachHooks.length)return t.currentRoute=n,t.history.push(n),t.afterEachHooks.forEach(function(e){return e(n,r)}),void e(n);t.beforeEachHooks[o++](n,r,function(e){!1===e?i(new Error("Navigation aborted")):a()})}a()})};return e}();

var router=new Router({routes:[{path:"/",component:"Home",meta:{title:"Home"}},{path:"/dashboard",component:"Dashboard",meta:{title:"Dashboard",requiresAuth:!0}},{path:"/settings",component:"Settings",meta:{title:"Settings",requiresAuth:!0}},{path:"/login",component:"Login",meta:{title:"Login",guestOnly:!0}},{path:"/404",component:"NotFound",meta:{title:"Not Found"}}]});router.beforeEach(function(e,t,n){var r=e.meta&&e.meta.requiresAuth;var i=AppConfig.auth&&AppConfig.auth.token;if(r&&!i)return n({path:"/login"});n()});
