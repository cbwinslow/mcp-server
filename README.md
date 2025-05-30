# MCP Server

[![Version](https://img.shields.io/github/v/release/cbwinslow/mcp-server?include_prereleases)](https://github.com/cbwinslow/mcp-server/releases)
[![License](https://img.shields.io/github/license/cbwinslow/mcp-server)](LICENSE)
[![Build Status](https://github.com/cbwinslow/mcp-server/workflows/CI/badge.svg)](https://github.com/cbwinslow/mcp-server/actions)

A robust Message Control Protocol (MCP) server implementation hosted on CloudFlare infrastructure, providing seamless AI tool integration capabilities.

## Overview

The MCP Server project implements a high-performance message control protocol server designed for AI tool integration. Hosted at mcp.cloudcurio.cc, it provides a scalable and secure platform for managing AI communication protocols.

### Key Features

- Real-time WebSocket communication
- REST API endpoints for system management
- Comprehensive AI tool integration
- Advanced security features
- Scalable CloudFlare infrastructure
- Monitoring and analytics dashboard

For detailed project specifications, see:
- [Project Plan](docs/PROJECT_PLAN.md)
- [Software Requirements Specification](docs/SRS.md)

## Quick Start

### Prerequisites

- Node.js 18.x or higher
- CloudFlare account with Workers/Pages access
- Domain access for cloudcurio.cc
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/cbwinslow/mcp-server.git
cd mcp-server
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configurations
```

4. Run development server:
```bash
npm run dev
```

## CloudFlare Setup

### Domain Configuration

1. Log into CloudFlare dashboard
2. Add subdomain mcp.cloudcurio.cc
3. Configure DNS settings:
```
Type    Name    Content             Proxy status
A       mcp     192.0.2.1          Proxied
CNAME   www     mcp.cloudcurio.cc  Proxied
```

### Workers Setup

1. Install Wrangler CLI:
```bash
npm install -g @cloudflare/wrangler
```

2. Configure Wrangler:
```bash
wrangler login
wrangler init
```

3. Deploy to CloudFlare:
```bash
wrangler publish
```

## Development Setup

### Local Development

1. Set up development environment:
```bash
npm run setup-dev
```

2. Start development server:
```bash
npm run dev
```

3. Run tests:
```bash
npm test
```

### Docker Development

1. Build container:
```bash
docker build -t mcp-server .
```

2. Run container:
```bash
docker run -p 3000:3000 mcp-server
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Process

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to your fork
5. Submit a pull request

### Code Standards

- Follow ESLint configuration
- Write tests for new features
- Update documentation
- Follow semantic versioning

## Documentation

- [API Documentation](docs/api/README.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](docs/deployment.md)
- [Security Policy](docs/SECURITY.md)

## System Architecture

The system is built on CloudFlare's infrastructure using:

- CloudFlare Workers for serverless computing
- CloudFlare Pages for static content
- WebSocket protocol for real-time communication
- JWT for authentication
- React for admin interface

## Monitoring and Analytics

Access the monitoring dashboard at:
https://mcp.cloudcurio.cc/admin

Features include:
- Real-time metrics
- System health monitoring
- Usage analytics
- Error tracking
- Performance metrics

## Security

Security features include:

- SSL/TLS encryption
- DDoS protection
- Rate limiting
- JWT authentication
- Role-based access control

For security issues, please see our [Security Policy](docs/SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Submit bug reports via GitHub Issues
- Join our [Discord community](https://discord.gg/mcp-server)
- Email support: support@cloudcurio.cc

## Roadmap

See our [Project Plan](docs/PROJECT_PLAN.md) for detailed development roadmap.

## Acknowledgments

- CloudFlare for infrastructure
- Contributors and maintainers
- Open source community

## Version History

See [CHANGELOG.md](CHANGELOG.md) for release history.

