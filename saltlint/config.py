# -*- coding: utf-8 -*-
# Copyright (c) 2019 Roald Nefs

import yaml
import os
import sys
import pathspec

# Import Salt libs
from salt.ext import six

import saltlint.utils


default_rulesdir = os.path.join(os.path.dirname(saltlint.utils.__file__), 'rules')


class SaltLintConfigError(Exception):
    pass


class SaltLintConfig(object):

    def __init__(self, options=dict()):
        self._options = options
        # Configuration file to use, defaults to ".salt-lint".
        config = options.get('c')
        file = config if config is not None else '.salt-lint'

        # Read the file contents
        if os.path.exists(file):
            with open(file, 'r') as f:
                content = f.read()
        else:
            content = None

        # Parse the content of the file as YAML
        self._parse(content)

    def _parse(self, content):
        config = dict()

        # Parse the YAML content
        if content:
            try:
                config = yaml.safe_load(content)
            except Exception as exc:
                raise SaltLintConfigError("invalid config: {}".format(exc))

        # Parse verbosity
        self.verbosity = self._options.get('verbosity', 0)
        if 'verbosity' in config:
            self.verbosity += config['verbosity']

        # Parse exclude paths
        self.exclude_paths = self._options.get('exclude_paths', [])
        if 'exclude_paths' in config:
            self.exclude_paths += config['exclude_paths']

        # Parse skip list
        skip_list = self._options.get('skip_list', [])
        if 'skip_list' in config:
            skip_list += config['skip_list']
        skip = set()
        for s in skip_list:
            skip.update(str(s).split(','))
        self.skip_list = frozenset(skip)

        # Parse tags
        self.tags = self._options.get('tags', [])
        if 'tags' in config:
            self.tags += config['tags']
        if isinstance(self.tags, six.string_types):
            self.tags = self.tags.split(',')

        # Parse use default rules
        use_default_rules = self._options.get('use_default_rules', False)
        if 'use_default_rules' in config:
            use_default_rules = use_default_rules or config['use_default_rules']

        # Parse rulesdir
        rulesdir = self._options.get('rulesdir', [])
        if 'rulesdir' in config:
            rulesdir += config['rulesdir']

        # Determine the rules directories
        if use_default_rules:
            self.rulesdirs = rulesdir + [default_rulesdir]
        else:
            self.rulesdirs = rulesdir or [default_rulesdir]

        # Parse colored
        self.colored = self._options.get(
            'colored',
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        )

        # Parse rule specific configuration, the configration can be listed by
        # the rule ID and/or tag.
        self.rules = dict()
        if 'rules' in config and isinstance(config['rules'], dict):
            # Read rule specific configuration from the config dict.
            for name, rule in six.iteritems(config['rules']):
                # Store the keys as strings.
                self.rules[str(name)] = dict()

                if 'ignore' not in rule:
                    continue

                if not isinstance(rule['ignore'], six.string_types):
                    raise SaltLintConfigError(
                        'invalid config: ignore should contain file patterns')

                # Retrieve the pathspec.
                self.rules[str(name)]['ignore'] = pathspec.PathSpec.from_lines(
                    'gitwildmatch', rule['ignore'].splitlines())

    def is_file_ignored(self, filepath, rule):
        rule = str(rule)
        if rule not in self.rules or 'ignore' not in self.rules[rule]:
            return False
        return self.rules[rule]['ignore'].match_file(filepath)
