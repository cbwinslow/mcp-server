import { Express, Request, Response } from 'express';

export const setupRoutes = (app: Express): void => {
  // Health check endpoint
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // Status endpoint
  app.get('/api/v1/status', (_req: Request, res: Response) => {
    res.json({
      status: 'operational',
      version: process.env.npm_package_version,
      environment: process.env.NODE_ENV,
    });
  });
};

