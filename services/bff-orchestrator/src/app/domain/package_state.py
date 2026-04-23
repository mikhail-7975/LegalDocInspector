from enum import Enum


class PackageState(str, Enum):
    created = "created"
    files_uploaded = "files_uploaded"
    extracting = "extracting"
    extracted = "extracted"
    form_editing = "form_editing"
    calculating = "calculating"
    calculated = "calculated"
    generating = "generating"
    documents_ready = "documents_ready"
    failed = "failed"
