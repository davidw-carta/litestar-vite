from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from litestar.plugins import CLIPlugin, InitPluginProtocol

if TYPE_CHECKING:
    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig

    from litestar_vite.config import ViteConfig


def set_environment(config: ViteConfig) -> None:
    """Configure environment for easier integration"""
    os.environ.setdefault("ASSET_URL", config.asset_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))
    os.environ.setdefault("VITE_PORT", str(config.port))
    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    if config.dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.dev_mode))


class VitePlugin(InitPluginProtocol, CLIPlugin):
    """Vite plugin."""

    __slots__ = ("_config",)

    def __init__(self, config: ViteConfig) -> None:
        """Initialize ``Vite``.

        Args:
            config: configure and start Vite.
        """
        self._config = config

    @property
    def config(self) -> ViteConfig:
        return self._config

    def on_cli_init(self, cli: Group) -> None:
        from litestar_vite.cli import vite_group

        cli.add_command(vite_group)
        return super().on_cli_init(cli)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """

        from litestar_vite.config import ViteTemplateConfig
        from litestar_vite.template_engine import ViteTemplateEngine

        app_config.template_config = ViteTemplateConfig(  # type: ignore[assignment]
            engine=ViteTemplateEngine,
            config=self._config,
            directory=self._config.template_dir,
        )
        set_environment(config=self._config)
        return app_config

    @contextmanager
    def server_lifespan(self, app: Litestar) -> Iterator[None]:
        import threading

        from litestar_vite.commands import execute_command

        if self.config.use_server_lifespan and self._config.dev_mode:
            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            vite_thread = threading.Thread(
                target=execute_command,
                args=[command_to_run],
            )
            try:
                vite_thread.start()
                yield
            finally:
                if vite_thread.is_alive():
                    vite_thread.join()
        else:
            yield
