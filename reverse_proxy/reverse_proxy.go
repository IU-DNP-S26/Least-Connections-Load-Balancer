package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

// server metadata for load balancing
type Server struct {
	Name        string // server name
	URL         string // URL path to server
	ServingReqs int    // number of currently serving requests by server
}

// server metadata to construct URL
type ServerMetadata struct {
	Address string // server address
	Port    string // server port number
	Scheme  string // protocol(HTTP or HTTPS)
}

// data structure to parse config with "servers" field
type Config struct {
	Servers []ServerMetadata `json:"servers"`
}

// least connections algorithm(choose server with minimal load)
func min_load_serv_idx(servers []Server) int {
	min_load_server_index := 0
	for i := 1; i < len(servers); i++ {
		if servers[i].ServingReqs < servers[min_load_server_index].ServingReqs {
			min_load_server_index = i
		}
	}

	return min_load_server_index
}

// logging server loads
func logServerLoads(servers []Server) {
	loads := make(map[string]int)
	for _, server := range servers {
		loads[server.Name] = server.ServingReqs
	}
	log.Printf("Current server loads: %v", loads)
}

// handler to count prime numbers
func markdownToPdfHandler(w http.ResponseWriter,
	r *http.Request, servers *[]Server, mu *sync.Mutex, client *http.Client) {

	startTime := time.Now()
	requestID := fmt.Sprintf("%d", time.Now().UnixNano()) // as unique identifier

	log.Printf("[%s] Received request: %s %s from %s", requestID, r.Method, r.URL.Path, r.RemoteAddr)

	// choose server with minimal load to redirect request
	mu.Lock()
	server_idx := min_load_serv_idx(*servers)
	(*servers)[server_idx].ServingReqs++ // increment number of currently serving requests
	// server details for logging
	selectedServer := (*servers)[server_idx].Name
	selectedURL := (*servers)[server_idx].URL
	currentLoad := (*servers)[server_idx].ServingReqs
	logServerLoads(*servers)
	mu.Unlock()

	log.Printf("[%s] Selected server: %s (URL: %s, New load: %d)",
		requestID, selectedServer, selectedURL, currentLoad)

	// decrement at the end of function
	defer func() {
		mu.Lock()
		(*servers)[server_idx].ServingReqs-- // decrement number of currently serving requests
		finalLoad := (*servers)[server_idx].ServingReqs
		mu.Unlock()

		elapsed := time.Since(startTime)
		log.Printf("[%s] Request completed to %s (Duration: %v, Server load now: %d)",
			requestID, selectedServer, elapsed, finalLoad)
	}()

	// send request
	log.Printf("[%s] Forwarding request to: %s%s",
		requestID, selectedURL, r.URL.RequestURI())

	req, err := http.NewRequest(r.Method, (*servers)[server_idx].URL+r.URL.RequestURI(), r.Body)
	if err != nil {
		log.Printf("[%s] ERROR: Failed to create request - %v", requestID, err)
		http.Error(w, "Bad request format", http.StatusBadRequest)
		return
	}
	req.Header = r.Header.Clone() // clone headers from client request
	req.Header.Set("X-Forwarded-For", r.RemoteAddr)

	// get response
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("[%s] ERROR: Backend server %s failed to respond - %v",
			requestID, selectedServer, err)
		http.Error(w, "Server response failed", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	log.Printf("[%s] Received response from %s (Status: %s)",
		requestID, selectedServer, resp.Status)

	// clone headers from server response
	for k, v := range resp.Header {
		for _, vv := range v {
			w.Header().Add(k, vv)
		}
	}

	// send response to client
	w.WriteHeader(resp.StatusCode)
	// track bytes written
	bytesWritten, err := io.Copy(w, resp.Body)
	if err != nil {
		log.Printf("[%s] ERROR: Failed to send response to client - %v", requestID, err)
	} else {
		log.Printf("[%s] Successfully sent %d bytes to client", requestID, bytesWritten)
	}
}

/* Arguments:
1st arg - reverse proxy port
2nd arg - path to config file
*/
func main() {
	// configure logging format
	log.SetFlags(log.LstdFlags | log.Lmicroseconds)
	log.Println("Service starting")

	args := os.Args
	if len(args) != 3 {
		log.Printf("ERROR: Invalid number of arguments. Expected 2, got %d", len(args)-1)
		log.Println("Usage: ./reverse-proxy <proxy_port> <config_file_path>")
		log.Println("Example: ./reverse-proxy 8080 ./config.json")
		return
	}
	reverse_proxy_port := args[1]
	config_file_path := args[2]

	// read config file
	data, err := os.ReadFile(config_file_path)
	if err != nil {
		log.Printf("ERROR: Failed to read config file - %v", err)
		return
	}

	// load servers metadata from json
	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		log.Printf("ERROR: Failed to parse JSON - %v", err)
		return
	}

	// create server data structures
	servers_metadata := config.Servers
	num_servers := len(servers_metadata)
	servers := []Server{}
	for i := 0; i < num_servers; i++ {
		server_metadata := servers_metadata[i] // get server metadata
		// construct URL
		url := server_metadata.Scheme + "://" + server_metadata.Address + ":" + server_metadata.Port
		serverName := "server" + strconv.Itoa(i+1)
		servers = append(servers, Server{serverName, url, 0})

		// ADDED - Detailed server configuration log
		log.Printf("  %s: %s -> %s (Scheme: %s, Address: %s, Port: %s)",
			serverName, serverName, url,
			server_metadata.Scheme, server_metadata.Address, server_metadata.Port)
	}

	var mu sync.Mutex // mutex to avoid race conditions
	client := &http.Client{
		// timeout configuration
		Timeout: 30 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	// create router and start reverse proxy
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		markdownToPdfHandler(w, r, &servers, &mu, client)
	})

	// healthcheck
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// endpoint to see current loads
	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()

		logServerLoads(servers)
		w.Header().Set("Content-Type", "application/json")
		stats := make(map[string]interface{})
		serverStats := make([]map[string]interface{}, len(servers))

		for i, server := range servers {
			serverStats[i] = map[string]interface{}{
				"name":             server.Name,
				"url":              server.URL,
				"serving_requests": server.ServingReqs,
			}
		}
		stats["servers"] = serverStats
		stats["timestamp"] = time.Now()
		json.NewEncoder(w).Encode(stats)
	})

	log.Printf("Starting reverse proxy on port %s", reverse_proxy_port)

	if err := http.ListenAndServe(":"+reverse_proxy_port, mux); err != nil {
		log.Printf("ERROR: Failed to start reverse proxy - %v", err)
		log.Println("Port may be already in use or insufficient permissions")
		return
	}
}
