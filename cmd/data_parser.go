package cmd

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type ConfluenceWebhook struct {
	Event string `json:"event"`
	Page  struct {
		ID    int    `json:"id"`
		Title string `json:"title"`
	} `json:"page"`
}

func handleConfluenceWebhook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var webhook ConfluenceWebhook
	if err := json.NewDecoder(r.Body).Decode(&webhook); err != nil {
		http.Error(w, "Invalid payload", http.StatusBadRequest)
		return
	}

	log.Printf("Confluence event: %s, Page: %s\n", webhook.Event, webhook.Page.Title)
	w.WriteHeader(http.StatusOK)
	if _, err := fmt.Fprintf(w, "Webhook processed"); err != nil {
		log.Printf("Error writing response: %v\n", err)
	}
}

func StartServer(port string) {
	config := LoadConfig()

	mux := http.NewServeMux()
	mux.HandleFunc("/webhook/confluence", handleConfluenceWebhook)
	mux.HandleFunc("/health", healthCheck)

	server := &http.Server{
		Addr:           ":" + port,
		Handler:        mux,
		ReadTimeout:    config.Server.ReadTimeout,
		WriteTimeout:   config.Server.WriteTimeout,
		IdleTimeout:    config.Server.IdleTimeout,
		MaxHeaderBytes: config.Server.MaxHeaderBytes,
	}

	// Channel to listen for interrupt signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start server in a goroutine
	go func() {
		log.Printf("Server listening on port %s\n", port)
		log.Printf("Environment: %s\n", config.App.Environment)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %v\n", err)
		}
	}()

	// Wait for interrupt signal
	sig := <-sigChan
	log.Printf("\nReceived signal: %v\n", sig)
	log.Println("Starting graceful shutdown...")

	// Create a context with timeout for graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), config.Server.ShutdownTimeout)
	defer cancel()

	// Gracefully shutdown the server
	if err := server.Shutdown(ctx); err != nil {
		log.Printf("Server shutdown error: %v\n", err)
		server.Close()
	}

	log.Println("Server shutdown completed")
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"healthy","timestamp":"%s"}`, time.Now().Format(time.RFC3339))
}
