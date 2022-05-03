import confuse
import re
import yaml

config = confuse.CachedConfiguration("trakt-scrobbler", "trakt_scrobbler")

# copy version from default config to user config if not present
temp_root = confuse.RootView(s for s in config.sources if not s.default)
if "version" not in temp_root:
    temp_root["version"] = config["version"].get()
    with open(config.user_config_path(), "w") as f:
        yaml.dump(temp_root.flatten(), f, Dumper=confuse.yaml_util.Dumper)
elif temp_root["version"].get() != config.sources[-1]["version"]:
    import logging
    logger = logging.getLogger("trakt_scrobbler")
    logger.warning(
        "Config version mismatch! Check configs at "
        f"{config.sources[-1].filename} and {config.user_config_path()}"
    )


class AnyDictValTemplate(confuse.Template):
    """Return True if any of the values for the specified keys are truth-y."""

    def __init__(self, keys: set[str], default=True):
        super().__init__(default)
        self.keys = keys

    def convert(self, value, view: confuse.ConfigView):
        if not isinstance(value, dict):
            raise confuse.ConfigTypeError(
                f'{view.name} must be a dict, not {type(value).__name__}')
        for k, v in value.items():
            if k in self.keys and v:
                return True

        return False


class BoolTemplate(confuse.Template):
    """A bool configuration value template.
    """
    def convert(self, value, view):
        """Check that the value is truth-y.
        """
        try:
            return bool(value)
        except TypeError as e:
            self.fail(f'must be coercible to bool, got {e}', view, True)
        except ValueError as e:
            self.fail(f'must be coercible to bool, got {e}', view, False)


class RegexPat(confuse.Template):
    """A regex configuration value template"""

    def convert(self, value, view) -> re.Pattern:
        """Check that the value is an regex.
        """
        try:
            return re.compile(value)
        except re.error as e:
            self.fail(u"malformed regex: '{}'. Error: {}".format(e.pattern, e), view)
        except TypeError as e:
            self.fail(u"Couldn't compile regex from '{}'. Error: {}".format(value, e),
                      view, type_error=True)
