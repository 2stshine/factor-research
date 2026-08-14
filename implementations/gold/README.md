# Query-only Gold implementations

This directory owns factor-specific SQL, manifest bindings, and parity inputs.
Each SQL file must remain a single parameterized read-only query over certified
Silver relations and must return `asset_id`, `as_of_date`, `value`, and `rank`.

Adding an implementation does not approve a factor and does not write Gold.
Only factors selected by campaign-wide multiple testing are eligible for
`campaign-verify-implementations`; that command compares Python and SQL on the
frozen discovery window and records the manifest and SQL hashes. Production
publication remains a separate explicitly approved operation.
