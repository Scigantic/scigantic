# Security

The client makes anonymous HTTPS requests to api.scigantic.com and, with the
`hf` extra, to huggingface.co through `huggingface_hub`. It stores no
credentials of its own; a Hugging Face token is read from the places
`huggingface_hub` already uses.

Report a vulnerability to aaron@scigantic.com. Please do not open a public issue for it.
