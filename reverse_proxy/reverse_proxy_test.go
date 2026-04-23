package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// ── min_load_serv_idx ────────────────────────────────────────────────────────

func TestMinLoadServIdx_AllAlive(t *testing.T) {
	servers := []Server{
		{Name: "s1", ServingReqs: 5, isAlive: true},
		{Name: "s2", ServingReqs: 2, isAlive: true},
		{Name: "s3", ServingReqs: 8, isAlive: true},
	}
	if got := min_load_serv_idx(servers); got != 1 {
		t.Errorf("expected index 1 (s2), got %d", got)
	}
}

func TestMinLoadServIdx_AllDead(t *testing.T) {
	servers := []Server{
		{Name: "s1", ServingReqs: 0, isAlive: false},
		{Name: "s2", ServingReqs: 0, isAlive: false},
	}
	if got := min_load_serv_idx(servers); got != -1 {
		t.Errorf("expected -1, got %d", got)
	}
}

func TestMinLoadServIdx_SkipDeadServers(t *testing.T) {
	servers := []Server{
		{Name: "s1", ServingReqs: 0, isAlive: false}, // dead, lowest load but should be skipped
		{Name: "s2", ServingReqs: 3, isAlive: true},
		{Name: "s3", ServingReqs: 1, isAlive: true},
	}
	if got := min_load_serv_idx(servers); got != 2 {
		t.Errorf("expected index 2 (s3), got %d", got)
	}
}

func TestMinLoadServIdx_EqualLoad_PicksFirst(t *testing.T) {
	servers := []Server{
		{Name: "s1", ServingReqs: 2, isAlive: true},
		{Name: "s2", ServingReqs: 2, isAlive: true},
	}
	if got := min_load_serv_idx(servers); got != 0 {
		t.Errorf("expected index 0 on tie, got %d", got)
	}
}

func TestMinLoadServIdx_Empty(t *testing.T) {
	if got := min_load_serv_idx([]Server{}); got != -1 {
		t.Errorf("expected -1 for empty list, got %d", got)
	}
}

func TestMinLoadServIdx_SingleAlive(t *testing.T) {
	servers := []Server{
		{Name: "s1", ServingReqs: 7, isAlive: true},
	}
	if got := min_load_serv_idx(servers); got != 0 {
		t.Errorf("expected index 0, got %d", got)
	}
}

// ── checkServerHealth ────────────────────────────────────────────────────────

func TestCheckServerHealth_Returns200(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			w.WriteHeader(http.StatusOK)
		}
	}))
	defer backend.Close()

	server := &Server{Name: "test", URL: backend.URL}
	client := &http.Client{Timeout: 5 * time.Second}

	if !checkServerHealth(server, client) {
		t.Error("expected healthy server to return true")
	}
}

func TestCheckServerHealth_Returns500(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer backend.Close()

	server := &Server{Name: "test", URL: backend.URL}
	client := &http.Client{Timeout: 5 * time.Second}

	if checkServerHealth(server, client) {
		t.Error("expected 500 response to return false")
	}
}

func TestCheckServerHealth_Unreachable(t *testing.T) {
	server := &Server{Name: "test", URL: "http://127.0.0.1:1"}
	client := &http.Client{Timeout: 500 * time.Millisecond}

	if checkServerHealth(server, client) {
		t.Error("expected unreachable server to return false")
	}
}

// ── markdownToPdfHandler ─────────────────────────────────────────────────────

func TestHandler_NoAliveServers(t *testing.T) {
	servers := []Server{
		{Name: "s1", URL: "http://127.0.0.1:1", isAlive: false},
	}
	var mu sync.Mutex
	client := &http.Client{}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	markdownToPdfHandler(rr, req, &servers, &mu, client)

	if rr.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rr.Code)
	}
}

func TestHandler_ForwardsToLeastLoaded(t *testing.T) {
	var hit string

	b1 := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hit = "s1"
		w.WriteHeader(http.StatusOK)
	}))
	defer b1.Close()

	b2 := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hit = "s2"
		w.WriteHeader(http.StatusOK)
	}))
	defer b2.Close()

	servers := []Server{
		{Name: "s1", URL: b1.URL, ServingReqs: 5, isAlive: true},
		{Name: "s2", URL: b2.URL, ServingReqs: 1, isAlive: true},
	}
	var mu sync.Mutex
	client := &http.Client{Timeout: 10 * time.Second}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	markdownToPdfHandler(rr, req, &servers, &mu, client)

	if hit != "s2" {
		t.Errorf("expected s2 (least connections) to be selected, got %s", hit)
	}
}

func TestHandler_ProxiesResponseBody(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("hello from backend"))
	}))
	defer backend.Close()

	servers := []Server{
		{Name: "s1", URL: backend.URL, ServingReqs: 0, isAlive: true},
	}
	var mu sync.Mutex
	client := &http.Client{Timeout: 10 * time.Second}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	markdownToPdfHandler(rr, req, &servers, &mu, client)

	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
	if body := rr.Body.String(); body != "hello from backend" {
		t.Errorf("unexpected body: %q", body)
	}
}

func TestHandler_CopiesResponseHeaders(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Custom-Header", "test-value")
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	servers := []Server{
		{Name: "s1", URL: backend.URL, ServingReqs: 0, isAlive: true},
	}
	var mu sync.Mutex
	client := &http.Client{Timeout: 10 * time.Second}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	markdownToPdfHandler(rr, req, &servers, &mu, client)

	if got := rr.Header().Get("X-Custom-Header"); got != "test-value" {
		t.Errorf("expected header X-Custom-Header=test-value, got %q", got)
	}
}

func TestHandler_DecreasesLoadAfterRequest(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	servers := []Server{
		{Name: "s1", URL: backend.URL, ServingReqs: 0, isAlive: true},
	}
	var mu sync.Mutex
	client := &http.Client{Timeout: 10 * time.Second}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	markdownToPdfHandler(rr, req, &servers, &mu, client)

	if servers[0].ServingReqs != 0 {
		t.Errorf("expected ServingReqs=0 after request completed, got %d", servers[0].ServingReqs)
	}
}

func TestHandler_BackendUnavailable_Returns502(t *testing.T) {
	servers := []Server{
		{Name: "s1", URL: "http://127.0.0.1:1", ServingReqs: 0, isAlive: true},
	}
	var mu sync.Mutex
	client := &http.Client{Timeout: 500 * time.Millisecond}

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	markdownToPdfHandler(rr, req, &servers, &mu, client)

	if rr.Code != http.StatusBadGateway {
		t.Errorf("expected 502, got %d", rr.Code)
	}
}

// ── /health endpoint ─────────────────────────────────────────────────────────

func TestHealthEndpoint(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	req := httptest.NewRequest("GET", "/health", nil)
	rr := httptest.NewRecorder()
	mux.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
	if rr.Body.String() != "OK" {
		t.Errorf("expected body 'OK', got %q", rr.Body.String())
	}
}

// ── /stats endpoint ──────────────────────────────────────────────────────────

func TestStatsEndpoint_ReturnsJSON(t *testing.T) {
	servers := []Server{
		{Name: "s1", URL: "http://localhost:8001", ServingReqs: 2, isAlive: true, LastCheck: time.Now()},
		{Name: "s2", URL: "http://localhost:8002", ServingReqs: 0, isAlive: false, LastCheck: time.Now()},
	}
	var mu sync.Mutex

	mux := http.NewServeMux()
	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		stats := make(map[string]interface{})
		serverStats := make([]map[string]interface{}, len(servers))
		for i, s := range servers {
			serverStats[i] = map[string]interface{}{
				"name":             s.Name,
				"url":              s.URL,
				"serving_requests": s.ServingReqs,
				"is_alive":         s.isAlive,
				"last_check":       s.LastCheck,
			}
		}
		stats["servers"] = serverStats
		stats["timestamp"] = time.Now()
		json.NewEncoder(w).Encode(stats)
	})

	req := httptest.NewRequest("GET", "/stats", nil)
	rr := httptest.NewRecorder()
	mux.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
	if ct := rr.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("expected Content-Type application/json, got %q", ct)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(rr.Body.Bytes(), &result); err != nil {
		t.Fatalf("failed to parse JSON response: %v", err)
	}
	if _, ok := result["servers"]; !ok {
		t.Error("response missing 'servers' field")
	}
	if _, ok := result["timestamp"]; !ok {
		t.Error("response missing 'timestamp' field")
	}

	serverList, ok := result["servers"].([]interface{})
	if !ok {
		t.Fatal("'servers' field is not an array")
	}
	if len(serverList) != 2 {
		t.Errorf("expected 2 servers, got %d", len(serverList))
	}
}
