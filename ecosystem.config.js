module.exports = {
  apps: [
    {
      name: "fte-orchestrator",
      script: "src/orchestrator.py",
      interpreter: "python",
      cwd: __dirname,
      autorestart: true,
      max_restarts: 10,
      watch: false,
      out_file: "logs/fte-orchestrator-out.log",
      error_file: "logs/fte-orchestrator-error.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        DEV_MODE: "true",
      },
    },
  ],
};
