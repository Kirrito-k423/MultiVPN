"""Safety boundaries of the diagnostic helper, without a VPN or Docker."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


runtime = module('runtime')
poc = module('poc')


class GuardTests(unittest.TestCase):
    def test_host_file_changes_do_not_change_effective_target_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source.json'
            effective = Path(temporary) / 'effective.json'
            source.write_text('[{"host":"192.0.2.1","port":22}]')
            with patch.object(runtime, 'SOURCE_CONFIG', source), patch.object(runtime, 'CONFIG', effective):
                runtime.snapshot_targets()
                source.write_text('[{"host":"192.0.2.99","port":443}]')
                self.assertEqual(runtime.targets(), [('192.0.2.1', 22)])

    def test_invalid_destination_or_port_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'targets.json'
            for target in ({'host': 'hostname.example', 'port': 22},
                           {'host': '192.0.2.1', 'port': True},
                           {'host': '192.0.2.1', 'port': 65536}):
                path.write_text(json.dumps([target]))
                with patch.object(runtime, 'CONFIG', path), self.assertRaises(ValueError):
                    runtime.targets()

    def test_plain_network_route_cannot_enable_forwarding(self):
        responses = [subprocess.CompletedProcess([], 0, json.dumps([{'dev': 'eth0'}])),
                     subprocess.CompletedProcess([], 0, json.dumps([{'linkinfo': {'info_kind': 'veth'}}]))]
        with patch.object(runtime, 'targets', return_value=[('192.0.2.1', 22)]), \
             patch.object(runtime, 'guard_hook'), patch.object(runtime, 'run', side_effect=responses) as run:
            with self.assertRaises(RuntimeError):
                runtime.allow()
            self.assertTrue(all(call.args[0][0] == 'ip' for call in run.call_args_list))

    def test_reject_is_inserted_without_flushing_existing_rules(self):
        with patch.object(runtime, 'targets', return_value=[('192.0.2.1', 22)]), \
             patch.object(runtime, 'run') as run:
            runtime.deny()
            args = run.call_args.args[0]
            self.assertIn('-I', args)
            self.assertIn('REJECT', args)
            self.assertNotIn('-F', args)

    def test_allows_bind_the_target_port_to_observed_tunnel(self):
        responses = [subprocess.CompletedProcess([], 0, '[{"dev":"tun0"}]'),
                     subprocess.CompletedProcess([], 0, '[{"linkinfo":{"info_kind":"tun"}}]'),
                     subprocess.CompletedProcess([], 0, '')]
        with patch.object(runtime, 'targets', return_value=[('192.0.2.1', 22)]), \
             patch.object(runtime, 'guard_hook'), patch.object(runtime, 'run', side_effect=responses) as run:
            runtime.allow()
            args = run.call_args.args[0]
            self.assertEqual(args[args.index('-o') + 1], 'tun0')
            self.assertEqual(args[args.index('--dport') + 1], '22')
            self.assertIn('ACCEPT', args)


class OwnershipTests(unittest.TestCase):
    def test_foreign_name_never_reaches_docker(self):
        with patch.object(poc, 'docker') as docker:
            with self.assertRaises(ValueError):
                poc.owned('production-service')
            docker.assert_not_called()

    def test_matching_prefix_without_owner_label_is_rejected(self):
        result = subprocess.CompletedProcess([], 0, '[{"Config":{"Labels":{}}}]')
        with patch.object(poc, 'docker', return_value=result), self.assertRaises(ValueError):
            poc.owned('multivpn-poc-foreign')

    def test_export_refuses_non_loopback_management_binding(self):
        info = {'NetworkSettings': {'Ports': {'22/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '22261'}]}}}
        options = SimpleNamespace(name='multivpn-poc-a')
        with patch.object(poc, 'owned', return_value=info), self.assertRaises(ValueError):
            poc.export(options)

    def test_export_does_not_replace_a_changed_guest_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target_file = directory / 'targets.json'
            target_file.write_text('[{"host":"192.0.2.1","port":22}]')
            known = directory / 'multivpn-poc-a-known-hosts'
            original = 'multivpn-poc-a-guest ssh-ed25519 ORIGINAL\n'
            known.write_text(original)
            info = {'NetworkSettings': {'Ports': {'22/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '22261'}]}},
                    'Mounts': [{'Destination': '/run/multivpn/targets.json', 'Source': str(target_file)}]}
            key = subprocess.CompletedProcess([], 0, 'ssh-ed25519 DIFFERENT guest\n')
            options = SimpleNamespace(name='multivpn-poc-a', directory=directory)
            targets = subprocess.CompletedProcess([], 0, '[{"host":"192.0.2.1","port":22}]')
            with patch.object(poc, 'owned', return_value=info), \
                 patch.object(poc, 'docker', side_effect=[targets, key]), self.assertRaises(ValueError):
                poc.export(options)
            self.assertEqual(known.read_text(), original)

    def test_unverified_installer_does_not_enter_build_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            installer = Path(temporary) / 'client.run'
            installer.write_text('unverified fixture')
            options = SimpleNamespace(installer=installer, sha256='0' * 64)
            with patch.object(poc, 'docker') as docker, self.assertRaises(ValueError):
                poc.build(options)
            docker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
