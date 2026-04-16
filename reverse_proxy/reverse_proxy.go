package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"sync"
)

// server metadata for proxy
type Server struct {
	Name        string // server name
	URL         string // URL path to server
	ServingReqs int    // number of currently serving requests by server
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

// handler to count prime numbers
func markdownToPdfHandler(w http.ResponseWriter,
	r *http.Request, servers []Server, mu *sync.Mutex, client *http.Client) {
	defer r.Body.Close()

	// choose server with minimal load to redirect request
	mu.Lock()
	server_idx := min_load_serv_idx(servers)
	servers[server_idx].ServingReqs++ // increment number of currently serving requests
	mu.Unlock()

	// decrement at the end of function
	defer func() {
		mu.Lock()
		servers[server_idx].ServingReqs-- // decrement number of currently serving requests
		mu.Unlock()
	}()

	// send request
	req, err := http.NewRequest(r.Method, servers[server_idx].URL+r.URL.RequestURI(), r.Body)
	if err != nil {
		http.Error(w, "Bad request format", http.StatusBadRequest)
		return
	}
	req.Header = r.Header.Clone() // clone headers from client request
	req.Header.Add("X-Forwarded-For", r.RemoteAddr)

	// get response
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Server response failed", http.StatusBadRequest)
		return
	}
	defer resp.Body.Close()

	// clone headers from server response
	for k, v := range resp.Header {
		for _, vv := range v {
			w.Header().Add(k, vv)
		}
	}

	// send response to client
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

func main() {
	args := os.Args // contains server ports
	if len(args) < 2 {
		fmt.Println("Invalid number of args")
		return
	}

	// create server data structures
	num_servers := len(args) - 1
	servers := []Server{}
	for i := 0; i < num_servers; i++ {
		url := "http://localhost:" + args[i+1]
		servers = append(servers, Server{"server" + strconv.Itoa(i+1), url, 0})
	}

	var mu sync.Mutex // mutex to avoid race conditions
	client := &http.Client{
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
		},
	}

	// create router and start reverse proxy
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		markdownToPdfHandler(w, r, servers, &mu, client)
	})
	http.ListenAndServe(":8080", mux)
}
