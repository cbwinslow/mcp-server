import express from 'express';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import cors from 'cors';
import dotenv from 'dotenv';
import { setupWebSocketServer } from './services/websocket';
import { errorHandler } from './middleware/error';
import { setupRoutes } from './routes';

// Load environment variables
dotenv.config();

// Create Express application
const app = express();
const port = process.env.PORT || 3001;

// Create HTTP server
const server = createServer(app);

// Create WebSocket server
const wss = new WebSocketServer({ server });

// Middleware setup
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: process.env.CORS_METHODS || ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: process.env.CORS_HEADERS || ['Content-Type', 'Authorization'],
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize WebSocket server
setupWebSocketServer(wss);

// Setup routes
setupRoutes(app);

// Error handling middleware (should be last)
app.use(errorHandler);

// Start server
server.listen(port, () => {
  console.log(`Server running in ${process.env.NODE_ENV || 'development'} mode`);
  console.log(`HTTP server listening at http://localhost:${port}`);
  console.log(`WebSocket server running at ws://localhost:${port}`);
});

