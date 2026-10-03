---
name: odoo-patterns
description: >
  Odoo development patterns for William's daily work (Cashea Odoo vertical, eagle workspace).
  Use when working with Odoo, Odoo modules/addons, __manifest__.py, models (_name/_inherit,
  compute, constrains, onchange), XML views/actions/menus, security (ir.model.access.csv,
  record rules), XML-RPC or JSON-RPC against Odoo, account.move, res.partner, Odoo migration
  v16 to v19, odoo-bin, --stop-after-init, or Odoo commit conventions.
  Usar cuando se trabaje con Odoo: crear o modificar un módulo/addon, manifiestos, modelos,
  vistas XML, seguridad, record rules, migración Odoo 16 a 19, correr/instalar/actualizar/testear
  módulos con odoo-bin, o integraciones RPC contra Odoo (v16 y v19).
---

# Odoo Patterns — workspace eagle

Patrones extraídos de módulos reales: `cashea_jumpcloud` (cashea-odoo v16 y v19), `l10n_ve_cashea` y `l10n_ve_bcv_rate` (cashea-odoo-v19), `unifica_base` / `unifica_payment_bancard` (unifica-addons, v19), `cashea_municipal_ret` / `cashea_allies_balance_report` / `cashea_custom_account` (cashea-odoo v16), `odoo19_backport` (pisa-addons, v18).

## Contexto del workspace

Todo corre desde `~/dev/eagle` (venv único en la raíz, core en `src-odoo/`, confs en `conf/`):

| Cliente | Repo addons | Conf | Versión | DB dev |
|---|---|---|---|---|
| Cashea (legacy) | `clients/cashea/cashea-odoo` | `conf/odoo-cashea.conf` | 16.0 | `cashea` |
| Cashea (nuevo) | `clients/cashea/cashea-odoo-v19` | — (v19) | 19.0 | — |
| Unifica | `clients/unifica/unifica-addons` | `conf/odoo-unifica.conf` | 19.0 | `ud19` |
| Pisa (penguin) | `clients/penguin/pisa-addons` | `conf/odoo.conf` | 19.0 | `pisa-19-dev` |

Los módulos viven UN nivel dentro de cada repo (raíz del repo = dir del `addons_path`). Nunca tocar `src-odoo/` ni editar `conf/*.conf` (contienen credenciales en texto plano — no leer ni exponer).

## Estructura de módulo

Layout mínimo (de `cashea_jumpcloud`) y completo (de `l10n_ve_cashea`):

```text
cashea_jumpcloud/                 l10n_ve_cashea/
├── __init__.py                   ├── __init__.py
├── __manifest__.py               ├── __manifest__.py
├── controllers/main.py           ├── data/            # XML + CSV (person_type_data.xml, account.islr.tax.csv)
├── data/                         ├── models/          # un archivo por modelo: account_move.py, res_partner.py...
├── models/                       ├── report/
├── views/                        ├── security/        # ir.model.access.csv + security.xml (record rules)
└── static/description/icon.png   ├── tests/
                                  ├── views/           # *_views.xml + menuitems.xml separado
                                  └── wizard/
```

### `__manifest__.py` (real, de `cashea_jumpcloud`)

```python
# -*- coding: utf-8 -*-
{
    'name': 'Cashea JumpCloud SSO',
    'version': '19.0.1.0.0',        # <serie>.<major>.<minor>.<patch> — 1er segmento = versión Odoo
    'category': 'Technical',
    'author': 'Grupo Cashea VE C.A.',
    'website': 'https://www.cashea.app',
    'summary': 'Inicio de sesión exclusivo vía JumpCloud (OIDC) y eliminación de la contraseña',
    'depends': ['auth_oidc'],
    'data': [
        'data/auth_oauth_provider_data.xml',
        'views/auth_templates.xml',
        'views/res_users_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

Convenciones del workspace:
- Orden de `data`: security → data → report → views → wizard → menuitems al final (ver `l10n_ve_cashea`).
- Localizaciones declaran `'countries': ['ve']` (l10n_ve_cashea) y categoría `Accounting/Localizations/Account Charts`.
- Módulos "glue" son thin + `'auto_install': True` (patrón `unifica_base`: `'category': 'Hidden'`, depends `['base']`).
- Licencias: `LGPL-3` (cashea/unifica), `OPL-1` en penguin (`odoo19_backport`).
- Datos que el usuario edita a mano después (providers, rules) van en `<odoo noupdate="1">`.

## Modelos

### Modelo nuevo (`_name`) — de `account_withholding.py` (v19)

```python
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

WITHHOLDING_STATE = [('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')]

class AccountWithholding(models.Model):
    _name = "account.withholding"
    _description = "Tax Withholdings"
    _order = "date desc, name desc"
    _check_company_auto = True

    name = fields.Char(string='Receipt number', index='trigram')
    state = fields.Selection(selection=WITHHOLDING_STATE, default='draft',
                             required=True, readonly=True, index=True)
    partner_id = fields.Many2one(comodel_name='res.partner', required=True,
                                 readonly=True, index=True)
    invoice_id = fields.Many2one(comodel_name='account.move', required=True,
                                 readonly=True, check_company=True, index=True)
```

- Selections como constantes módulo-level (`WITHHOLDING_TYPE`, `WITHHOLDING_STATE`).
- Siempre `comodel_name=` explícito en Many2one; `index=True` en campos de búsqueda; `index='trigram'` para Char buscables.
- `_check_company_auto = True` + `check_company=True` en relaciones multi-company.

### Herencia (`_inherit`) — de `res_partner.py` (l10n_ve_cashea)

```python
class Partner(models.Model):
    _inherit = "res.partner"

    vat = fields.Char(tracking=True, copy=False)   # redeclarar solo los atributos que cambian
    person_type_id = fields.Many2one(
        comodel_name='person.type',
        domain="[('is_company', '=', is_company)]",
        tracking=True, copy=False,
    )
    person_type_code = fields.Char(related='person_type_id.code', store=True)
```

Campos de negocio en partner llevan `tracking=True, copy=False`.

### Compute — sumar líneas (patrón dominante)

```python
@api.depends('line_ids', 'line_ids.tax_base_amount', 'line_ids.tax_amount',
             'line_ids.amount')
def _compute_amount(self):
    for rec in self:
        tax_amount = amount = 0.0
        for line in rec.line_ids:
            tax_amount += line.tax_amount
            amount += line.amount
        rec.tax_amount = tax_amount
        rec.amount = amount
```

### Constrains

**v19 — `models.Constraint`** (nuevo API, de `res_partner.py` v19):

```python
_unique_vat = models.Constraint(
    "EXCLUDE (vat WITH =) WHERE (parent_id IS NULL)",
    "There is already a contact with the same VAT!"
)
```

**v16 — `_sql_constraints`** (de `cashea_allies_balance_report/models/top_up_certificates.py`):

```python
_sql_constraints = [
    ('uniq_code', "UNIQUE(NULLIF(name, '/'))", 'El código de certificado ya existe.'),
    ('check_period', 'CHECK(date_from <= date_to)', 'Las fechas deben ser válidas.'),
]
```

**Constraint Python con escape hatch por contexto** (real: users/companies son partners y rompen la validación fiscal):

```python
@api.constrains('person_type_id', 'vat', 'country_id')
def _check_fiscal_partner_constrains(self):
    if self.env.context.get('skip_check_fiscal_partner_constrains'):
        return
    for partner in self:
        if partner.type in ('contact', 'invoice') and partner.country_id.code == 'VE':
            if not partner.vat:
                raise ValidationError(_("The 'VAT' field must be set."))

# En res.users / res.company:
@api.model_create_multi
def create(self, vals_list):
    self = self.with_context(skip_check_fiscal_partner_constrains=True)
    return super().create(vals_list)
```

### Onchange — limpiar dependientes

```python
@api.onchange('type')
def _clean_withholding_tax(self):
    if self.type != 'service':
        self.islr_tax_id = False
        self.municipal_tax_id = False
```

### Referenciar registros XML sin reventar

Patrón de `cashea_jumpcloud/models/res_users.py`:

```python
JUMPCLOUD_PROVIDER_XMLID = 'cashea_jumpcloud.provider_jumpcloud'  # constante módulo-level

@api.model
def _jumpcloud_only_active(self):
    provider = self.env.ref(JUMPCLOUD_PROVIDER_XMLID, raise_if_not_found=False)
    return bool(provider and provider.sudo().enabled)
```

Overrides de flujo: delegar en `super()` y rechazar el caso prohibido (no reimplementar):

```python
def _check_credentials(self, credential, env):          # firma v19: dict credential + env
    auth_info = super()._check_credentials(credential, env)
    if auth_info.get('auth_method') == 'password' and self.sudo()._jumpcloud_only_active():
        raise AccessDenied()
    return auth_info
```

## Vistas, acciones y menús

### Vista list + form (v19, de `account_withholding_views.xml`)

```xml
<record id="account_withholding_view_list" model="ir.ui.view">
    <field name="name">account.withholding.view.list</field>
    <field name="model">account.withholding</field>
    <field name="arch" type="xml">
        <list create="false" edit="false">
            <field name="partner_id" string="Supplier"
                   column_invisible="context.get('default_withholding_type') not in ('supplier_iva', 'supplier_islr')"/>
            <field name="tax_amount" optional="hide"/>
            <field name="company_id" optional="hide" groups="base.group_multi_company"/>
            <field name="state" widget="badge" decoration-info="state == 'draft'"
                   decoration-success="state == 'posted'" decoration-danger="state == 'cancel'"/>
        </list>
    </field>
</record>
```

Form con header de estados + botón inteligente:

```xml
<form create="0">
    <header>
        <button name="button_post" type="object" string="Post"
                invisible="state != 'draft'" class="oe_highlight"/>
        <field name="state" widget="statusbar" statusbar_visible="draft,posted"/>
    </header>
    <sheet>
        <div class="oe_button_box" name="button_box">
            <button name="button_open_journal_entry" class="oe_stat_button" icon="fa-bars"
                    type="object" invisible="state != 'posted' or not move_id"/>
        </div>
        ...
    </sheet>
</form>
```

### Acción + menú

Acción parametrizada por contexto (misma vista, N menús):

```xml
<record id="account_withholding_supplier_iva_action" model="ir.actions.act_window">
    <field name="name">Withholding IVA</field>
    <field name="res_model">account.withholding</field>
    <field name="view_mode">list,form</field>
    <field name="domain">[('withholding_type', '=', 'supplier_iva')]</field>
    <field name="context">{'default_withholding_type': 'supplier_iva'}</field>
</record>
```

Menús en un `views/menuitems.xml` propio, colgados de menús estándar de `account`:

```xml
<menuitem id="menu_account_withholding_supplier_iva"
          action="account_withholding_supplier_iva_action"
          parent="account.menu_finance_payables" sequence="80"/>

<menuitem id="menu_l10n_ve_configuration" name="Localization"
          parent="account.menu_finance_configuration" sequence="100">
    <menuitem id="menu_action_account_ut" action="action_account_ut" sequence="10"/>
</menuitem>
```

## Seguridad

### `security/ir.model.access.csv` (de `l10n_ve_cashea`)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_person_type,access.person.type,model_person_type,base.group_user,1,0,0,0
access_account_withholding,access.account.withholding,model_account_withholding,base.group_user,1,1,1,1
```

- `id` = `access_<modelo_con_underscores>`; `model_id:id` = `model_<modelo_con_underscores>`.
- Catálogos/config: solo lectura (`1,0,0,0`); documentos de trabajo: full (`1,1,1,1`).
- El CSV va SIEMPRE en `data` del manifest (antes que las vistas) o el módulo no instala.

### Record rules — `security/security.xml`

```xml
<odoo>
    <data noupdate="1">
        <record id="account_withholding_company_rule" model="ir.rule">
            <field name="name">Account Withholding multi-company</field>
            <field name="model_id" ref="model_account_withholding"/>
            <field name="domain_force">[('company_id', 'in', company_ids)]</field>
        </record>
    </data>
</odoo>
```

Todo modelo nuevo con `company_id` lleva su regla multi-company con `company_ids` (variable de eval del rule).

## RPC contra Odoo

### Cliente XML-RPC (external API)

Patrón estándar para scripts contra las instancias (credenciales SIEMPRE por env var, nunca hardcodeadas — regla del workspace):

```python
import os
import xmlrpc.client

URL, DB = "http://localhost:8069", "ud19"        # o cashea / pisa-19-dev
USER, PWD = os.environ["ODOO_USER"], os.environ["ODOO_API_KEY"]

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PWD, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

partners = models.execute_kw(DB, uid, PWD, 'res.partner', 'search_read',
    [[('country_id.code', '=', 'VE'), ('vat', '!=', False)]],
    {'fields': ['name', 'vat', 'person_type_code'], 'limit': 100})

move_id = models.execute_kw(DB, uid, PWD, 'account.move', 'create',
    [{'move_type': 'entry', 'ref': 'RPC test'}])
models.execute_kw(DB, uid, PWD, 'account.move', 'action_post', [[move_id]])
```

Nota: con `cashea_jumpcloud` activado, la autenticación por contraseña se rechaza también vía RPC (`_check_credentials`) — usar **API keys**, que conservan `auth_method` propio.

### Controller JSON-RPC server-side (v19, de `unifica_payment_bancard/controllers/main.py`)

```python
from odoo import http
from odoo.http import request

class BancardController(http.Controller):

    @http.route('/payment/bancard/confirm', type='jsonrpc', auth='public',
                methods=['POST'], csrf=False)
    def bancard_confirm_transaction(self):
        data = request.get_json_data()          # v19: body JSON explícito
        operation_data = data.get('operation', {})
        if not operation_data:
            return {'status': 'error', 'message': 'No operation data'}
        ...

    @http.route('/payment/bancard/register_card', type='jsonrpc', auth='user')
    def bancard_register_card_start(self, partner_id, origin_url=None, **kwargs):
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'error': 'Partner not found'}
```

En v16 el tipo era `type='json'`; en v19 se renombró a `type='jsonrpc'`.

## Migración v16 → v19

Estrategia Cashea (documentada en `clients/cashea/v19_migration_strategy.md`): **rewrite deliberado, no upgrade**. Se extraen las reglas de negocio del v16 (3MIT + cashea_*) y se reimplementan limpias en módulos propios v19 (`l10n_ve_cashea`, `l10n_ve_edi_tfhka`, `l10n_ve_bcv_rate`). No hay carpetas `migrations/` con pre/post-migrate en los repos: la migración es por reconstrucción de módulos + carga de datos.

Diferencias de versión que YA aparecen en el código:

| Concepto | v16 (cashea-odoo) | v19 (cashea-odoo-v19 / unifica) |
|---|---|---|
| Vista de lista | `<tree>` | `<list>` (`<list create="false">`) |
| Visibilidad/estados | `attrs="{'invisible': [('type','!=','cash')]}"` | expresión directa: `invisible="state != 'draft'"`, `column_invisible="..."` |
| Constraints SQL | `_sql_constraints = [(name, sql, msg)]` | `_atributo = models.Constraint(sql, msg)` |
| Auth | `_check_credentials(self, password)` | `_check_credentials(self, credential, env)` → dict `{'uid','auth_method','mfa'}` |
| Controller JSON | `type='json'` | `type='jsonrpc'` + `request.get_json_data()` |
| Manifest | version `16.0.x.y.z` | version `19.0.x.y.z`, `'countries': [...]` en l10n |

Checklist al portar un módulo v16 → v19: bump de `version` en manifest, `tree`→`list`, reescribir todos los `attrs`/`states` a expresiones, `_sql_constraints`→`models.Constraint`, revisar firmas de overrides (auth, search contract), `type='json'`→`type='jsonrpc'`.

## Instalar / actualizar / testear (odoo-bin)

Siempre desde `~/dev/eagle`, con el venv raíz y la conf del cliente:

```bash
# Instalar módulo (init) y salir
venv/bin/python src-odoo/odoo/odoo-bin -c conf/odoo-unifica.conf -d ud19 \
  -i unifica_payment_bancard --stop-after-init --no-http --log-level=info

# Actualizar módulo tras cambios en Python/XML
venv/bin/python src-odoo/odoo/odoo-bin -c conf/odoo-cashea.conf -d cashea \
  -u cashea_jumpcloud --stop-after-init --no-http

# Correr los tests de un módulo (suite propia solamente)
venv/bin/python src-odoo/odoo/odoo-bin -c conf/odoo-unifica.conf -d test_db \
  --test-enable --stop-after-init -i unifica_payment_bancard \
  --test-tags /unifica_payment_bancard

# Varios módulos
... -i mod1,mod2 --test-tags /mod1,/mod2
```

- Cambios solo-Python a veces cargan sin `-u`, pero XML/data/security SIEMPRE requieren `-u`.
- Debug interactivo: configs de `launch.json` del workspace (Cashea / pisa / Odoo Granite / Odoo Unifica).
- Gotcha zsh del workspace: `noclobber` activo (`>` no sobreescribe → usar `>|`).

### Tests — patrón real (de `l10n_ve_cashea/tests/test_res_partner_constraints.py`)

```python
from psycopg2 import IntegrityError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

@tagged('post_install', '-at_install')
class TestPartnerConstraints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.person_type_pjdo = cls.env.ref('l10n_ve_cashea.person_type_pjdo')

    def test_unique_vat_same_parent_not_allowed(self):
        self._create_partner(name='Partner 1', vat='J-12345678-9')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            partner_2 = self._create_partner(name='Partner 2', vat='J-12345678-9')
            partner_2.flush_recordset(['vat', 'parent_id'])   # forzar el constraint SQL
```

- `@tagged('post_install', '-at_install')` para tests que dependen de data cargada.
- Constraints SQL: `flush_recordset()` + `assertRaises(IntegrityError)` + `mute_logger('odoo.sql_db')`.
- Helpers `_create_partner(**kwargs)` con defaults para reducir ruido.

## Commits y PRs (convención Odoo, enforced por unifox-ci en unifica)

```text
[TAG] module: short description (imperativo, < 72 chars)
```

Tags válidos: `[ADD]` `[FIX]` `[UPD]` `[REF]` `[REM]` `[MOV]` `[IMP]` `[REL]` `[MERGE]` `[REV]` `[CLN]` `[LINT]` `[PERF]` `[I18N]` `[CLA]`

Ejemplos: `[FIX] l10n_ve_cashea: reject invalid PJDO VAT format`, `[ADD] cashea_jumpcloud: block password auth when SSO active`.

PR: cuerpo con `## Purpose` (el porqué) / `## Changes` (bullets por scope, máx 6) / `## Notes` (breaking/migración). En unifica-addons: rama base **`19.0`**, remote via host SSH `github-we`, y la CI comitea version-bump al branch del PR → hacer `git pull` después de abrir/actualizar el PR.
