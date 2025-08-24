from DocTemplateReplacer import DocTemplateReplacer
from DocLawsuitReplacer import DocLawsuitReplacer


def create_document(config_filename: str, template_filename: str, output_filename: str = "output.docx") -> None:
    replacer = DocTemplateReplacer()
    replacer.make_instance(config_filename, template_filename, output_filename)


def create_document_2(config_filename: str, template_filename: str, output_filename: str = "output2.docx") -> None:
    replacer = DocLawsuitReplacer()
    replacer.make_instance(config_filename, template_filename, output_filename)


if __name__ == "__main__":
    config_template_1 = "lawsuit_create.json"
    template_filename_1 = "template.docx"
    output_filename = "output.docx"
    # create_document(config_template, template_filename_1, output_filename)

    config_template_2 = "lawsuits.json"
    template_filename_2 = "calculation_template.docx"
    create_document_2(config_template_2, template_filename_2)
