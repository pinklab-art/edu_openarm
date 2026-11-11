from openarm_mini import udev

ATTRS = {'idVendor': '1a86', 'idProduct': '55d3', 'serial': 'A1B2C3', 'kernels': '1-2.3'}


def test_build_rule_uses_serial():
    rule = udev.build_rule('left', ATTRS)
    assert 'ATTRS{serial}=="A1B2C3"' in rule
    assert 'KERNELS' not in rule
    assert 'SYMLINK+="openarm_mini_left"' in rule


def test_build_rule_without_serial_uses_usb_port():
    rule = udev.build_rule('right', dict(ATTRS, serial=None))
    assert 'KERNELS=="1-2.3"' in rule
    assert 'serial' not in rule


def test_merge_rules_replaces_same_arm_only():
    content = udev.merge_rules('', 'left', udev.build_rule('left', dict(ATTRS, serial='OLD')))
    content = udev.merge_rules(content, 'right', udev.build_rule('right', dict(ATTRS, serial='RIGHT')))
    merged = udev.merge_rules(content, 'left', udev.build_rule('left', ATTRS))
    assert merged.count('openarm_mini_left') == 1
    assert '"OLD"' not in merged
    assert '"A1B2C3"' in merged and '"RIGHT"' in merged
    assert merged.startswith(udev.RULES_HEADER)


def test_resolve_conflicts_drops_duplicate_serials():
    resolved = udev.resolve_conflicts({'left': dict(ATTRS, kernels='1-2'),
                                       'right': dict(ATTRS, kernels='1-3')})
    assert resolved['left']['serial'] is None and resolved['right']['serial'] is None
    distinct = udev.resolve_conflicts({'left': ATTRS, 'right': dict(ATTRS, serial='OTHER')})
    assert distinct['right']['serial'] == 'OTHER'
