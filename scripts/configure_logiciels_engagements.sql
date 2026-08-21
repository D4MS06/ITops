-- ITops — configuration locale : modules Logiciels et Engagements
-- À exécuter après le démarrage initial d'ITops (schéma MariaDB déjà créé).
-- Le script est idempotent : il met à jour les éléments portant les mêmes clés.

START TRANSACTION;

INSERT INTO custom_services (
    code, label, is_active, is_technical, credentials_enabled, child_enabled,
    child_label, sort_order, icon, color, description, treeview_config,
    allow_export, allow_import, created_at, updated_at
) VALUES
(
    'logiciels', 'Logiciels', 1, 0, 0, 0, 'Éléments liés', 120, 'package', '#3b82f6',
    'Catalogue des logiciels, éditeurs, versions et licences.',
    '{"tile":{"show_count":true},"relationship_inheritance":{},"notification_rules":[],"automation_rules":[]}',
    1, 1, NOW(), NOW()
),
(
    'engagements', 'Engagements', 1, 0, 0, 0, 'Éléments liés', 130, 'file-text', '#f59e0b',
    'Suivi des contrats, abonnements, renouvellements et montants.',
    '{"tile":{"show_count":true},"relationship_inheritance":{},"notification_rules":[],"automation_rules":[{"id":"echeance_j30","enabled":true,"trigger":{"type":"date","field_key":"date_echeance","offset_days":-30},"conditions":[{"field_key":"statut","operator":"not_equals","value":"Terminé"}],"actions":[{"type":"set_field","field_key":"statut","value":"À renouveler"},{"type":"notify"},{"type":"email","template_type":"engagement_echeance_j30","recipient_kind":"address","recipient_value":""}]},{"id":"echeance_depassee","enabled":true,"trigger":{"type":"date","field_key":"date_echeance","offset_days":0},"conditions":[{"field_key":"statut","operator":"not_equals","value":"Terminé"}],"actions":[{"type":"set_field","field_key":"statut","value":"Échu"},{"type":"notify"}]}]}',
    1, 1, NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    label = VALUES(label), is_active = VALUES(is_active), icon = VALUES(icon), color = VALUES(color),
    description = VALUES(description), treeview_config = VALUES(treeview_config), updated_at = NOW();

-- Les tuiles du portail et leurs droits administrateur sont crees ici aussi.
-- Ainsi le script reste complet meme s'il est execute pendant que le service est deja demarre.
INSERT INTO auth_modules (code, label, route_path, is_active, sort_order) VALUES
    ('service_logiciels', 'Logiciels', '/#service=logiciels', 1, 1120),
    ('service_engagements', 'Engagements', '/#service=engagements', 1, 1130)
ON DUPLICATE KEY UPDATE
    label = VALUES(label), route_path = VALUES(route_path), is_active = VALUES(is_active), sort_order = VALUES(sort_order);

INSERT IGNORE INTO auth_role_modules (role_code, module_code) VALUES
    ('admin', 'service_logiciels'),
    ('admin', 'service_engagements');

-- Modele utilise par l'action e-mail de la regle d'echeance J-30.
-- Sans destinataire explicite, l'envoi utilise les destinataires SMTP par defaut
-- definis dans les parametres de notifications de l'application.
INSERT IGNORE INTO notification_templates (
    code, label, module_code, task_type, subject_template, body_template,
    is_active, is_default
) VALUES (
    'engagement_echeance_j30', 'Echeance d''engagement a J-30', 'engagements',
    'engagement_echeance_j30',
    'Echeance a renouveler dans 30 jours - {{record.id}}',
    'L''engagement {{record.id}} arrive a echeance dans 30 jours. Consultez la fiche Engagements pour preparer son renouvellement.',
    1, 0
);

INSERT INTO custom_service_fields (
    service_code, field_key, label, field_kind, required, options, default_value, sort_order,
    list_source_kind, shared_list_code, show_in_list, searchable, unique_value, placeholder,
    help_text, min_value, max_value, track_history, inline_editable, batch_editable, quick_filter
) VALUES
('logiciels','nom','Nom','text',1,'','',10,'local','',1,1,1,'','',NULL,NULL,1,1,0,0),
('logiciels','editeur','Éditeur','text',0,'','',20,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('logiciels','version','Version','text',0,'','',30,'local','',1,1,0,'','',NULL,NULL,1,1,0,0),
('logiciels','type_licence','Type de licence','list',0,'Propriétaire,Open source,SaaS,Gratuiciel','Propriétaire',40,'local','',1,1,0,'','',NULL,NULL,1,1,1,1),
('logiciels','statut','Statut','list',1,'À évaluer,Validé,Déployé,Retiré','À évaluer',50,'local','',1,1,0,'','',NULL,NULL,1,1,1,1),
('engagements','reference','Référence','text',1,'','',10,'local','',1,1,1,'','',NULL,NULL,1,1,0,0),
('engagements','objet','Objet','text',1,'','',20,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('engagements','fournisseur','Fournisseur','text',0,'','',30,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('engagements','statut','Statut','list',1,'Brouillon,Actif,À renouveler,Échu,Terminé','Brouillon',40,'local','',1,1,0,'','',NULL,NULL,1,1,1,1),
('engagements','date_debut','Date de début','date',0,'','',50,'local','',1,1,0,'','',NULL,NULL,1,1,0,0),
('engagements','date_echeance','Date d’échéance','date',1,'','',60,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('engagements','montant_annuel','Montant annuel','number',0,'','',70,'local','',1,1,0,'','',0,NULL,1,1,0,0)
ON DUPLICATE KEY UPDATE
    label=VALUES(label), field_kind=VALUES(field_kind), required=VALUES(required), options=VALUES(options),
    default_value=VALUES(default_value), sort_order=VALUES(sort_order), show_in_list=VALUES(show_in_list),
    searchable=VALUES(searchable), track_history=VALUES(track_history), inline_editable=VALUES(inline_editable),
    batch_editable=VALUES(batch_editable), quick_filter=VALUES(quick_filter);

INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction, display_label,
    required, is_active, filter_candidates_by_shared_relation, show_indirect_relations, record_display_mode, sort_order
)
SELECT 'logiciels', 'engagements', 'est couvert par', 'many_to_many', 'out', 'Engagements associés',
       0, 1, 0, 0, 'standard', 10
WHERE NOT EXISTS (
    SELECT 1 FROM custom_service_relations
    WHERE source_service_code='logiciels' AND target_service_code='engagements' AND verb='est couvert par'
);

COMMIT;

-- Après import, créer le modèle e-mail « engagement_echeance_j30 » dans
-- Paramètres > Notifications > Templates, puis renseigner le destinataire de
-- l'action e-mail dans le module Engagements.
