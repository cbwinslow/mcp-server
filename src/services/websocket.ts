import WebSocket from 'ws';
import { WebSocketServer } from 'ws';

export const setupWebSocketServer = (wss: WebSocketServer): void => {
  wss.on('connection', (ws: WebSocket) => {
    console.log('Client connected');

    // Send welcome message
    ws.send(JSON.stringify({
      type: 'connection',
      message: 'Connected to MCP Server',
      timestamp: new Date().toISOString(),
    }));

    // Handle incoming messages
    ws.on('message', (data: string) => {
      try {
        const message = JSON.parse(data.toString());
        console.log('Received:', message);

        // Echo the message back
        ws.send(JSON.stringify({
          type: 'response',
          data: message,
          timestamp: new Date().toISOString(),
        }));
      } catch (error) {
        console.error('Error processing message:', error);
        ws.send(JSON.stringify({
          type: 'error',
          message: 'Invalid message format',
          timestamp: new Date().toISOString(),
        }));
      }
    });

    // Handle client disconnection
    ws.on('close', () => {
      console.log('Client disconnected');
    });

    // Handle connection errors
    ws.on('error', (error: Error) => {
      console.error('WebSocket error:', error);
    });
  });
};

