---
name: itops-custom-modules
description: Configure or extend ITops custom modules, including fields, documents, relations, automation, and conditional validation.
---

# ITops custom modules

Use this skill when creating, configuring, or evolving a custom ITops module. Prefer the shared custom-service engine; do not add module-specific lifecycle, document, relation, or automation code when the shared configuration can express the need.

## Configuration order

1. Define stable fields and shared lists first.
2. Enable document categories and choose a stable folder source.
3. Configure relations and their cardinality. Use a required relation only when it is always required.
4. Configure automations and conditional validation in step 4 of the module editor.

## Documents

- A document category is represented by the field selected as its display anchor.
- The `document_linked` trigger targets that field/category when a file is explicitly linked in ITops.
- The automation editor only offers compatible fields: configured document categories for a document trigger, date fields for a date trigger, numeric fields for a threshold, and all fields for a field-change trigger.
- Use the `set_field_from_event` action to prefill an empty field from the linked document date. It never overwrites a manually entered value.
- The document list and record view display a direct link for one linked file, or a consultation view for several files. PDFs open in the browser; other formats download normally.

## Automation

Available triggers include record creation or update, field change, date, threshold, relation change, document link, import, synchronization, and inactivity.

Available actions include setting a field, pre-filling an empty field from an event, notification, email/task creation, and adding or removing a relation. Configure the action from the UI rather than using technical identifiers when possible.

## Conditional validation

Use a conditional validation rule when a field is required only for a particular value, for example:

- if `mode_achat` equals `Hors marché`, require `fournisseur_hors_marche`;
- if `statut` equals `Réception partielle`, require `elements_manquants`.

Conditional validation currently applies to fields. A relation that is always required must use the relation's built-in required setting; do not claim that conditional required relations are supported until the shared relation contract is extended.

## Verification

- Verify cardinality and required relation behavior.
- Verify documents are linked in ITops, not merely present in SMB.
- Test each automation with a real record and confirm manual values are preserved.
- Run the focused automation tests and the project build after changes to the shared engine.
