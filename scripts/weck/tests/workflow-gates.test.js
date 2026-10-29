'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { evaluatePrMainGate } = require('../pr-main-gate');
const { findTicketKeys, buildTicketReminder } = require('../ticket-key-reminder');

const odooRemote = 'git@github.com:cashea-bnpl/cashea-odoo-v19.git';
const otherRemote = 'git@github.com:cashea-bnpl/erp-service.git';

test('gh pr create without --base asks in an Odoo repo (default branch is main)', () => {
  const r = evaluatePrMainGate('gh pr create --title "[FIX] sale: x" --body y', odooRemote);
  assert.equal(r.decision, 'ask');
  assert.match(r.reason, /A PRODUCCION/);
});

test('gh pr create targeting main asks in all flag spellings', () => {
  for (const flag of ['--base main', '--base=main', '-B main', '-Bmain']) {
    const r = evaluatePrMainGate(`gh pr create ${flag} --fill`, odooRemote);
    assert.equal(r?.decision, 'ask', flag);
  }
});

test('gh pr create targeting another branch does not ask', () => {
  assert.equal(evaluatePrMainGate('gh pr create --base qa --fill', odooRemote), null);
  assert.equal(evaluatePrMainGate('gh pr create -B staging --fill', odooRemote), null);
});

test('non-Odoo repos and unrelated commands are ignored', () => {
  assert.equal(evaluatePrMainGate('gh pr create --base main', otherRemote), null);
  assert.equal(evaluatePrMainGate('gh pr view 12 --json state', odooRemote), null);
  assert.equal(evaluatePrMainGate('git push origin HEAD', odooRemote), null);
});

test('gh pr create chained after another command is still detected', () => {
  const r = evaluatePrMainGate('git push -u origin HEAD && gh pr create --base main', odooRemote);
  assert.equal(r?.decision, 'ask');
});

test('findTicketKeys extracts EP and ODOO keys once, uppercased', () => {
  assert.deepEqual(findTicketKeys('implementá ep-535 y EP-535, también ODOO-12'), ['EP-535', 'ODOO-12']);
  assert.deepEqual(findTicketKeys('sin tickets acá, solo HELP-1 o STEP-5'), []);
});

test('findTicketKeys ignores Odoo version paths but keeps real ODOO keys', () => {
  assert.deepEqual(findTicketKeys('~/dev/cashea/odoo-src/odoo-16.0 y odoo-19'), []);
  assert.deepEqual(findTicketKeys('ODOO-19 y ep-7'), ['ODOO-19', 'EP-7']);
});

test('buildTicketReminder names the keys and the In Progress order', () => {
  const text = buildTicketReminder(['EP-535']);
  assert.match(text, /EP-535/);
  assert.match(text, /In Progress/);
  assert.match(text, /ANTES de escribir código o crear la rama/);
});
