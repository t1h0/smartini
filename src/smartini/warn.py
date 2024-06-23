"""General warnings used across smartini."""

# Index warnings
_index_warning = lambda index_type: (
    f"{index_type} indexing directly on an entity (in contrast to on a Schema)"
    " might yield unwanted slots because entities might only hold a subset"
    " of all Schema slots."
)


slice_index = _index_warning("Slice")
negative_index = _index_warning("Negative")

# Manipulation warnings

slot_manipulation = (
    "Adding/removing slots to/from an entity directly (in contrast to through a Schema)"
    " will liekly lead to inconsistencies in between entities and between entities"
    " and Schema."
)
