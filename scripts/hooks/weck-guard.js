#!/usr/bin/env node
'use strict';
/**
 * weck-guard — hook PreToolUse propio de William.
 * Bloquea escrituras a rutas intocables: core de Odoo (src-odoo), checkouts
 * vendorizados (unifica/odoo, unifica/enterprise), keystores de firma y
 * entornos virtuales. NUNCA bloquea por error propio (siempre exit 0 ante fallo).
 *
 * Convención Claude Code: exit 2 en PreToolUse => bloquea la tool y muestra
 * stderr al modelo. exit 0 (pasando el payload por stdout) => permite.
 */

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => (raw += c));
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(raw || '{}');
    const tool = data.tool_name || '';
    if (!/^(Write|Edit|MultiEdit|NotebookEdit)$/.test(tool)) {
      process.stdout.write(raw);
      process.exit(0);
    }
    const ti = data.tool_input || {};
    const p = String(ti.file_path || ti.path || ti.notebook_path || '');

    const PROTEGIDO = [
      { re: /\/src-odoo\//, por: 'core de Odoo (src-odoo) — intocable segun CLAUDE.md de eagle' },
      { re: /\/dev\/unifica\/(odoo|enterprise)\//, por: 'checkout vendorizado de Odoo/Enterprise (solo referencia; enterprise es propietario)' },
      { re: /\.keystore$/, por: 'keystore de firma (Play Store) — nunca editar ni commitear' },
      { re: /\/\.venv\/|\/venv\/(lib|bin|include)\//, por: 'entorno virtual (paquetes instalados, no se editan a mano)' },
    ];

    for (const g of PROTEGIDO) {
      if (g.re.test(p)) {
        process.stderr.write(
          '[weck-guard] BLOQUEADO: ' + p + '\n' +
          'Razon: ' + g.por + '.\n' +
          'Si es intencional, edita el archivo a mano o ajusta ~/.claude/scripts/hooks/weck-guard.js\n'
        );
        process.exit(2);
      }
    }
    process.stdout.write(raw);
    process.exit(0);
  } catch (e) {
    // Ante cualquier error del guard, permitir (nunca romper el flujo de tools).
    process.stdout.write(raw);
    process.exit(0);
  }
});
