import WebSocket from 'ws';

interface MCPMessage {
  type: string;
  payload: any;
}

export const handleMessage = async (ws: WebSocket, message: string): Promise<void> => {
  try {
    const parsedMessage: MCPMessage = JSON.parse(message.toString());
    
    switch (parsedMessage.type) {
      case 'ping':
        ws.send(JSON.stringify({ type: 'pong', payload: { timestamp: Date.now() } }));
        break;
      
      // Add more message type handlers here
      
      default:
        ws.send(JSON.stringify({ type: 'error', message: 'Unknown message type' }));
    }
  } catch (error) {
    throw new Error(`Error parsing message: ${error}`);
  }
};

