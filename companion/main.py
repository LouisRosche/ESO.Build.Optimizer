#!/usr/bin/env python3
"""
ESO Build Optimizer - Companion App
Cross-platform tray application for syncing SavedVariables to cloud.

Usage:
    python main.py                  # Run with GUI tray icon
    python main.py --headless       # Run without GUI (for servers/scripts)
    python main.py --config FILE    # Use custom config file
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('companion.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger('ESOBuildOptimizer')


class CompanionApp:
    """Main application class for the companion app."""

    def __init__(self, config_path: Optional[Path] = None, headless: bool = False):
        self.config_path = config_path or Path('config.json')
        self.headless = headless
        self.running = False
        self.watcher = None
        self.sync_client = None
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or create defaults."""
        default_config = {
            'api_url': 'https://api.esobuildoptimizer.com',
            'sync_interval_seconds': 30,
            'eso_path': None,  # Auto-detect
            'offline_mode': False,
            'debug': False,
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f'Loaded config from {self.config_path}')
            except Exception as e:
                logger.warning(f'Failed to load config: {e}, using defaults')
        else:
            # Create default config file
            self._save_config(default_config)

        return default_config

    def _save_config(self, config: dict):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f'Saved config to {self.config_path}')
        except Exception as e:
            logger.error(f'Failed to save config: {e}')

    def _setup_watcher(self):
        """Initialize the SavedVariables file watcher."""
        try:
            from watcher import SavedVariablesWatcher, find_eso_path

            # Find ESO path
            eso_path = self.config.get('eso_path')
            if not eso_path:
                eso_path = find_eso_path()
                if eso_path:
                    self.config['eso_path'] = str(eso_path)
                    self._save_config(self.config)

            if not eso_path:
                logger.error('Could not find ESO installation. Please set eso_path in config.json')
                return False

            # Create watcher with callback
            self.watcher = SavedVariablesWatcher(
                eso_path=Path(eso_path),
                addon_name='ESOBuildOptimizer',
                callback=self._on_data_changed,
            )
            return True

        except ImportError as e:
            logger.error(f'Failed to import watcher module: {e}')
            return False

    def _setup_sync(self):
        """Initialize the cloud sync client."""
        try:
            from sync import SyncClient

            self.sync_client = SyncClient(
                api_url=self.config.get('api_url', 'https://api.esobuildoptimizer.com'),
                offline_cache=True,
            )
            return True

        except ImportError as e:
            logger.error(f'Failed to import sync module: {e}')
            return False

    def _on_data_changed(self, data: dict):
        """Callback when SavedVariables data changes."""
        logger.info('SavedVariables updated, queueing sync...')

        if self.sync_client and not self.config.get('offline_mode'):
            # Queue data for sync
            pending_runs = data.get('pendingSync', {}).get('runs', [])
            for run in pending_runs:
                self.sync_client.queue_run(run)

    async def _sync_loop(self):
        """Background sync loop."""
        interval = self.config.get('sync_interval_seconds', 30)

        while self.running:
            try:
                if self.sync_client and not self.config.get('offline_mode'):
                    await self.sync_client.sync_pending()
            except Exception as e:
                logger.error(f'Sync error: {e}')

            await asyncio.sleep(interval)

    def _run_headless(self):
        """Run in headless mode (no GUI)."""
        logger.info('Starting in headless mode...')

        # Setup signal handlers
        def handle_signal(signum, frame):
            logger.info('Received shutdown signal')
            self.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Start watcher in background thread
        if self.watcher:
            watcher_thread = threading.Thread(target=self.watcher.start, daemon=True)
            watcher_thread.start()

        # Run sync loop
        self.running = True
        asyncio.run(self._sync_loop())

    def _run_with_tray(self):
        """Run with system tray icon."""
        try:
            import pystray
            from PIL import Image
        except ImportError:
            logger.warning('pystray/PIL not available, falling back to headless mode')
            return self._run_headless()

        logger.info('Starting with system tray...')

        # Create tray icon
        def create_icon():
            # Simple icon - 64x64 green circle
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            for x in range(64):
                for y in range(64):
                    dx, dy = x - 32, y - 32
                    if dx*dx + dy*dy <= 28*28:
                        img.putpixel((x, y), (100, 200, 100, 255))
            return img

        def on_status(icon, item):
            if self.watcher:
                status = 'Watching' if self.watcher.is_running else 'Stopped'
            else:
                status = 'Not initialized'
            logger.info(f'Status: {status}')

        def on_sync_now(icon, item):
            logger.info('Manual sync triggered')
            if self.sync_client:
                asyncio.run(self.sync_client.sync_pending())

        def on_quit(icon, item):
            logger.info('Quit requested')
            self.stop()
            icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem('Status', on_status),
            pystray.MenuItem('Sync Now', on_sync_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', on_quit),
        )

        icon = pystray.Icon(
            'ESOBuildOptimizer',
            create_icon(),
            'ESO Build Optimizer',
            menu,
        )

        # Start watcher in background
        if self.watcher:
            watcher_thread = threading.Thread(target=self.watcher.start, daemon=True)
            watcher_thread.start()

        # Start sync loop in background
        self.running = True
        sync_thread = threading.Thread(
            target=lambda: asyncio.run(self._sync_loop()),
            daemon=True
        )
        sync_thread.start()

        # Run tray icon (blocks)
        icon.run()

    def start(self):
        """Start the companion app."""
        logger.info('ESO Build Optimizer Companion starting...')

        # Setup components
        if not self._setup_watcher():
            logger.warning('Watcher setup failed')

        if not self._setup_sync():
            logger.warning('Sync client setup failed')

        # Run appropriate mode
        if self.headless:
            self._run_headless()
        else:
            self._run_with_tray()

    def stop(self):
        """Stop the companion app."""
        logger.info('Stopping companion app...')
        self.running = False

        if self.watcher:
            self.watcher.stop()


def main():
    parser = argparse.ArgumentParser(
        description='ESO Build Optimizer Companion App',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run without GUI (no tray icon)'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to config file (default: config.json)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    app = CompanionApp(
        config_path=args.config,
        headless=args.headless,
    )

    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
    except Exception as e:
        logger.error(f'Fatal error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
