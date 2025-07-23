from DocTemplateReplacer import DocTemplateReplacer


def create_document(config_filename: str, template_filename: str, output_filename: str = "output.docx") -> None:
    replacer = DocTemplateReplacer()
    replacer.make_instance(config_filename, template_filename, output_filename)


if __name__ == "__main__":
    config_filename = "lawsuit_create.json"
    template_filename = "template.docx"
    output_filename = "output.docx"
    create_document(config_filename, template_filename, output_filename)
