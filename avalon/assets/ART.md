# Arte do núcleo Avalon

Criada com a ferramenta integrada de geração de imagens, a partir do pedido do autor: bolinha dourada
em pixel art com efeitos de raios verdes e vermelhos. Não foi usada a API/CLI de geração de imagens.

O arquivo de produção `orb-atlas.png` usa uma grade 4 × 4 de quadros de 96 × 96 pixels, com canal alpha.
É uma derivação de runtime da arte gerada: extração da grade, redução nearest-neighbor e máscara
binária para transparência por chave de cor do Tk/Windows. A arte gerada original não é necessária
para executar o programa. `orb-atlas.json` define estados e duração dos quadros.

Prompt de geração (especificação):

> Production pixel-art sprite sheet for a floating desktop assistant called Avalon. One transparent
> RGBA atlas, four columns and four rows, no labels or borders. The same centered spherical golden
> energy core in every cell, metallic pixel shading and warm halo. Four successive frames per row:
> calm golden idle, listening with emerald-green lightning, processing/speaking with green and crimson
> lightning, alert with crimson lightning and green accents. Keep sphere position and size consistent.
> Crisp retro 16-bit pixel clusters, transparent background, no scenery, characters or text.
