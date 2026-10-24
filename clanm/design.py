"""Tokens GTK adaptados de Prints & Paints / App.vue + docs/agents/UI.md.

Cores de interface, tipografia e espaçamento ficam centralizados aqui.
Cores dos LEDs são dados do usuário e não pertencem à paleta da interface.
"""
FONT='Inter, Sans'
SPACE={'xs':4,'sm':8,'md':12,'lg':16,'xl':24,'xxl':32}
TYPE={'title':30,'section':22,'card':17,'body':15,'small':14,'label':13,'aux':12}
WEIGHT={'regular':400,'medium':500,'semibold':600,'bold':700}
THEMES={
 'dark':{'page':'#0b0d12','surface':'#15181f','elevated':'#1d2028','input':'#1d2028','hover':'#252932','active':'#312e81','active_text':'#c7d2fe','text':'#e4e7ee','secondary':'#a8b0c0','tertiary':'#8b93a5','border':'#252932','border_hover':'#3a4150','accent':'#818cf8','accent_hover':'#a5b4fc','primary':'#4f46e5','on_primary':'#ffffff','success':'#6ee7b7','warning':'#fcd34d','error':'#fca5a5'},
 'light':{'page':'#f6f7fb','surface':'#ffffff','elevated':'#ffffff','input':'#f0f2f8','hover':'#e2e5ef','active':'#e0e7ff','active_text':'#4f46e5','text':'#1a1d29','secondary':'#4a5568','tertiary':'#5f6b7c','border':'#dde1ec','border_hover':'#c5cad8','accent':'#4f46e5','accent_hover':'#4338ca','primary':'#4f46e5','on_primary':'#ffffff','success':'#047857','warning':'#92400e','error':'#b91c1c'},
}

def css(theme):
    colors=THEMES[theme]
    declarations='\n'.join(f'@define-color pp_{name} {value};' for name,value in colors.items())
    return (declarations+f'''
    * {{font-family: {FONT};font-size:{TYPE['small']}px;}}
    window {{background:@pp_page;color:@pp_text;}}
    headerbar {{background:@pp_surface;color:@pp_text;border-bottom:1px solid @pp_border;box-shadow:none;}}
    headerbar .title {{font-size:{TYPE['small']}px;font-weight:{WEIGHT['semibold']};}}
    label.hero {{font-size:{TYPE['title']}px;font-weight:{WEIGHT['bold']};color:@pp_text;}}
    label.sub {{color:@pp_secondary;font-size:{TYPE['label']}px;}}
    label.section {{font-size:{TYPE['card']}px;font-weight:{WEIGHT['semibold']};color:@pp_text;}}
    label.status {{color:@pp_success;font-size:{TYPE['label']}px;}}
    label.warning {{color:@pp_warning;}}
    label.error {{color:@pp_error;}}
    notebook {{background:@pp_surface;border:1px solid @pp_border;border-radius:12px;}}
    notebook>header {{background:@pp_surface;border-bottom:1px solid @pp_border;}}
    notebook tab {{padding:{SPACE['md']}px {SPACE['xl']}px;color:@pp_secondary;}}
    notebook tab:checked {{background:@pp_active;color:@pp_active_text;border-bottom:2px solid @pp_accent;}}
    notebook tab:checked label {{color:@pp_active_text;}}
    button {{background-image:none;background:@pp_surface;color:@pp_text;border:1px solid @pp_border_hover;border-radius:8px;
             padding:{SPACE['sm']}px {SPACE['md']}px;min-height:24px;font-weight:{WEIGHT['medium']};}}
    button:hover {{background:@pp_hover;}}
    button:focus {{outline:2px solid @pp_accent;outline-offset:2px;}}
    button.suggested-action {{background:@pp_primary;border-color:@pp_primary;color:@pp_on_primary;font-weight:{WEIGHT['semibold']};}}
    button.suggested-action:hover {{background:@pp_accent_hover;}}
    button:disabled {{color:@pp_tertiary;background:@pp_input;opacity:0.65;}}
    entry,spinbutton,combobox button {{background:@pp_input;color:@pp_text;border-color:@pp_border_hover;}}
    scale trough {{background:@pp_hover;min-height:4px;}}
    scale highlight {{background:@pp_accent;}}
    scale slider {{background:@pp_accent;border:2px solid @pp_surface;min-width:16px;min-height:16px;}}
    checkbutton {{color:@pp_secondary;}}
    checkbutton check:checked {{background:@pp_primary;color:@pp_on_primary;}}
    .actionbar {{background:@pp_elevated;border-top:1px solid @pp_border;padding:{SPACE['lg']}px;}}
    .preview {{background:@pp_input;border-radius:12px;border:1px solid @pp_border;}}
    .feedback {{background:@pp_surface;border:1px solid @pp_border;border-radius:8px;padding:{SPACE['md']}px;}}
    ''').encode()


def rgb_token(theme,name):
    value=THEMES[theme][name].lstrip('#')
    return tuple(int(value[n:n+2],16)/255 for n in (0,2,4))
