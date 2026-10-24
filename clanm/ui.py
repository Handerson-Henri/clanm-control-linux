import copy
import json
from pathlib import Path
import subprocess
import threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib
from . import backend
from .protocol import KEYBOARD_MODES,MOUSE_MODES,ACTIONS,keyboard_packet,mouse_lighting_sequence,MOUSE_LIGHT_EFFECTS,MOUSE_SPEED_MODES,MOUSE_BRIGHTNESS_MODES

ROOT=Path(__file__).resolve().parent.parent
from .design import css,SPACE,THEMES,rgb_token

def label(text,style=None):
    widget=Gtk.Label(label=text,xalign=0);widget.set_line_wrap(True)
    if style:widget.get_style_context().add_class(style)
    return widget

def combo(values):
    widget=Gtk.ComboBoxText()
    for value in values:widget.append_text(str(value))
    widget.set_active(0);return widget

def spin(low,high,step=1):
    widget=Gtk.SpinButton.new_with_range(low,high,step);widget.set_numeric(True);return widget

def set_combo(widget,value):
    for i,row in enumerate(widget.get_model()):
        if row[0]==str(value):widget.set_active(i);return
    raise ValueError(f'Opção desconhecida: {value}')

def color_value(widget):
    c=widget.get_rgba();return '#%02x%02x%02x'%(round(c.red*255),round(c.green*255),round(c.blue*255))

class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title='Clanm Control Linux')
        self.set_default_size(1080,800);self.set_position(Gtk.WindowPosition.CENTER)
        self.connect('destroy',lambda *_: Gtk.main_quit() if Gtk.main_level() else None)
        self.connect('delete-event',self.before_close)
        self.busy=False
        try:self.theme=json.loads((backend.STATE/'appearance.json').read_text()).get('theme','dark')
        except (OSError,ValueError):self.theme='dark'
        if self.theme not in THEMES:self.theme='dark'
        self.theme_provider=Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.theme_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        header=Gtk.HeaderBar(title='Clanm Control',subtitle='CL-TK87 · MK043');header.set_show_close_button(True)
        self.set_titlebar(header)
        self.theme_button=Gtk.Button();self.theme_button.set_tooltip_text('Alternar tema claro e escuro');self.theme_button.connect('clicked',self.toggle_theme);header.pack_end(self.theme_button)
        self.apply_theme()
        access=Gtk.Button(label='Liberar acesso USB');access.connect('clicked',self.permissions);header.pack_end(access)
        refresh=Gtk.Button(label='Detectar');refresh.connect('clicked',lambda *_:self.refresh());header.pack_end(refresh)
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=SPACE['lg']);outer.set_border_width(SPACE['xl']);self.add(outer)
        outer.pack_start(label('Controle de iluminação','hero'),False,False,0)
        outer.pack_start(label('Escolha uma cor, ajuste o efeito e guarde suas preferências em um perfil.','sub'),False,False,0)
        self.devices=label('Detectando…','status');outer.pack_start(self.devices,False,False,0)
        notebook=Gtk.Notebook();outer.pack_start(notebook,True,True,0)
        self.k={};self.m={};self.recovery={};self.undo_buttons={}
        notebook.append_page(self.keyboard_page(),Gtk.Label(label='Teclado CL-TK87'))
        notebook.append_page(self.mouse_page(),Gtk.Label(label='Mouse MK043'))
        notebook.append_page(self.help_page(),Gtk.Label(label='Perfis e ajuda'))
        self.status=label('Escolher uma cor não aplica a alteração. Use Aplicar quando estiver pronto.','sub')
        self.status.get_style_context().add_class('feedback')
        outer.pack_start(self.status,False,False,0)
        self.populate(backend.default_config())
        try:
            saved=json.loads((backend.STATE/'last-applied.json').read_text())
            values=backend.default_config();values.update(saved);self.validate(values);self.populate(values)
            self.status.set_text('Exibindo os últimos valores enviados por este aplicativo; não é uma leitura do hardware.')
        except (OSError,ValueError,KeyError,TypeError):pass
        self.refresh()
        GLib.timeout_add_seconds(4,self.refresh)

    def before_close(self,*_):
        if self.busy:
            self.status.set_text('Aguarde a operação USB terminar antes de fechar.')
            return True
        return False

    def apply_theme(self):
        self.theme_provider.load_from_data(css(self.theme))
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',self.theme=='dark')
        self.theme_button.set_label('Tema claro' if self.theme=='dark' else 'Tema escuro')
        if hasattr(self,'kpreview'):self.kpreview.queue_draw();self.mpreview.queue_draw()

    def toggle_theme(self,*_):
        self.theme='light' if self.theme=='dark' else 'dark'
        self.apply_theme()
        backend.atomic_json(backend.STATE/'appearance.json',{'theme':self.theme})

    def page(self):
        shell=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=SPACE['lg']);box.set_border_width(SPACE['xl']);scroll.add(box)
        box._shell=shell;shell.pack_start(scroll,True,True,0)
        return shell,box

    def action_bar(self,box,kind,button):
        footer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=SPACE['sm']);footer.get_style_context().add_class('actionbar')
        row=Gtk.Box(spacing=SPACE['sm'])
        blue=Gtk.Button(label='Voltar ao azul testado');blue.connect('clicked',lambda *_:self.restore_blue(kind))
        undo=Gtk.Button(label='Desfazer');undo.set_tooltip_text('Restaura a iluminação anterior salva nesta versão. Não é o padrão de fábrica.');undo.connect('clicked',lambda *_:self.undo(kind))
        row.pack_start(undo,False,False,0);row.pack_start(blue,False,False,0);row.pack_end(button,False,False,0)
        footer.pack_start(row,False,False,0)
        footer.pack_start(label('As ações alteram apenas a iluminação deste dispositivo.','sub'),False,False,0)
        self.recovery[kind]=blue;self.undo_buttons[kind]=undo
        box._shell.pack_end(footer,False,False,0)

    def grid(self,box):
        grid=Gtk.Grid(column_spacing=SPACE['xl'],row_spacing=SPACE['lg']);box.pack_start(grid,False,False,0);return grid

    def row(self,grid,n,title,widget):
        field_label=label(title,'sub');field_label.set_mnemonic_widget(widget);field_label.get_accessible().set_name(title)
        widget.get_accessible().set_name(title)
        grid.attach(field_label,0,n,1,1);widget.set_hexpand(True);grid.attach(widget,1,n,1,1)

    def color(self):
        button=Gtk.ColorButton();button.set_title('Escolher cor');return button

    def preview(self,box,kind):
        area=Gtk.DrawingArea();area.set_size_request(360,100);area.get_style_context().add_class('preview');area.get_accessible().set_name('Prévia ilustrativa de iluminação')
        area.connect('draw',self.draw_preview,kind);box.pack_start(area,False,False,0)
        return area

    def keyboard_page(self):
        scroll,box=self.page()
        box.pack_start(label('Iluminação do teclado','section'),False,False,0)
        self.kpreview=self.preview(box,'keyboard')
        grid=self.grid(box)
        self.k['mode']=combo(KEYBOARD_MODES);self.row(grid,0,'Efeito',self.k['mode'])
        self.k['color']=self.color();self.row(grid,1,'Cor',self.color_panel(self.k,'keyboard'))
        self.k['brightness']=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,4,1);self.k['brightness'].set_digits(0);self.row(grid,2,'Brilho · 0 apaga / 4 máximo',self.k['brightness'])
        self.k['speed']=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,5,1);self.k['speed'].set_digits(0);self.row(grid,3,'Velocidade · 0 lenta / 5 rápida',self.k['speed'])
        self.k['direction']=combo(['Esquerda','Direita']);self.row(grid,4,'Direção do efeito',self.k['direction'])
        self.k['random']=Gtk.CheckButton(label='Cores aleatórias nos efeitos compatíveis');box.pack_start(self.k['random'],False,False,0)
        self.k['color'].connect('color-set',lambda *_:self.kpreview.queue_draw())
        box.pack_start(label('18 efeitos do protocolo Evision. Nem todo efeito usa cor, direção ou velocidade.','sub'),False,False,0)
        self.kapply=Gtk.Button(label='Aplicar no teclado');self.kapply.get_style_context().add_class('suggested-action');self.kapply.connect('clicked',lambda *_:self.apply('keyboard'))
        self.action_bar(box,'keyboard',self.kapply)
        return scroll

    def color_panel(self,controls,kind):
        panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=SPACE['sm'])
        panel.pack_start(controls['color'],False,False,0)
        controls['hex']=label('','sub');panel.pack_start(controls['hex'],False,False,0)
        presets=Gtk.Box(spacing=SPACE['sm'])
        def choose(button,value):
            c=Gdk.RGBA();c.parse(value);controls['color'].set_rgba(c);changed()
        def changed(*_):
            controls['hex'].set_text('Cor selecionada: '+color_value(controls['color']).upper()+' · escolher não aplica')
            if hasattr(self,'kpreview') and kind=='keyboard':self.kpreview.queue_draw()
            if hasattr(self,'mpreview') and kind=='mouse':self.mpreview.queue_draw()
        controls['color'].connect('color-set',changed)
        for title,value in [('Vermelho puro','#ff0000'),('Verde puro','#00ff00'),('Azul puro','#0000ff'),('Branco','#ffffff')]:
            button=Gtk.Button(label=title);button.connect('clicked',choose,value);presets.pack_start(button,False,False,0)
        panel.pack_start(presets,False,False,0)
        return panel

    def mouse_page(self):
        scroll,box=self.page()
        box.pack_start(label('Iluminação do mouse','section'),False,False,0)
        box.pack_start(label('Escolha um efeito nativo e ajuste sua iluminação. DPI, sensibilidade e botões ficam fora destas ações.','sub'),False,False,0)
        self.mpreview=self.preview(box,'mouse')
        grid=self.grid(box)
        self.m['mode']=combo(MOUSE_LIGHT_EFFECTS);self.row(grid,0,'Iluminação',self.m['mode'])
        self.m['color']=self.color();self.row(grid,1,'Cor',self.color_panel(self.m,'mouse'))
        self.m['brightness']=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,255,1);self.m['brightness'].set_digits(0)
        self.row(grid,2,'Brilho · 0 apagado / 255 máximo',self.m['brightness'])
        self.m['speed']=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,4,1);self.m['speed'].set_digits(0)
        self.row(grid,3,'Velocidade · 0 lenta / 4 rápida',self.m['speed'])
        self.mouse_hint=label('','sub');box.pack_start(self.mouse_hint,False,False,0)
        self.m['mode'].connect('changed',lambda *_:self.mouse_capabilities())
        self.mouse_capabilities()
        box.pack_start(label('Novos efeitos e ritmos ainda precisam de conferência visual no seu mouse. As animações são executadas pelo próprio dispositivo.','sub'),False,False,0)
        self.mapply=Gtk.Button(label='Aplicar no mouse');self.mapply.get_style_context().add_class('suggested-action');self.mapply.connect('clicked',lambda *_:self.apply('mouse'))
        self.action_bar(box,'mouse',self.mapply)
        return scroll

    def mouse_capabilities(self):
        mode=MOUSE_LIGHT_EFFECTS.get(self.m['mode'].get_active_text(),0)
        self.m['speed'].set_sensitive(mode in MOUSE_SPEED_MODES)
        self.m['brightness'].set_sensitive(mode in MOUSE_BRIGHTNESS_MODES)
        self.m['color'].set_sensitive(mode!=0)
        hint='A velocidade altera somente o efeito dos LEDs, não o ponteiro.' if mode in MOUSE_SPEED_MODES else 'Este efeito não tem velocidade ajustável no protocolo do mouse.'
        if mode in (3,4,9,10,11):hint+=' Alguns modos usam também a paleta já existente no mouse.'
        self.mouse_hint.set_text(hint)

    def help_page(self):
        scroll,box=self.page()
        box.pack_start(label('Perfis portáteis','section'),False,False,0)
        box.pack_start(label('Salve suas escolhas em JSON e guarde o arquivo para usar depois de formatar. Importar um perfil só preenche a tela; você escolhe quando aplicar. Nenhuma conta, senha ou sessão é coletada.','sub'),False,False,0)
        actions=Gtk.Box(spacing=SPACE['md'])
        for title,callback in [('Salvar perfil…',self.export_profile),('Carregar perfil…',self.import_profile)]:
            button=Gtk.Button(label=title);button.connect('clicked',callback);actions.pack_start(button,False,False,0)
        box.pack_start(actions,False,False,0)
        box.pack_start(label('Primeiro uso','section'),False,False,0)
        box.pack_start(label('1. Clique em Liberar acesso USB e autentique na janela do sistema.\n2. Se continuar sem acesso, retire e conecte o dispositivo e clique em Detectar.\n3. Escolha um efeito, cor ou perfil e clique em Aplicar.\n4. Confira fisicamente o resultado antes de salvar como seu perfil preferido.'),False,False,0)
        box.pack_start(label('Recuperar uma alteração','section'),False,False,0)
        box.pack_start(label('Voltar ao azul testado muda somente a iluminação para azul fixo. Desfazer restaura a iluminação anterior salva nesta versão: leitura real de oito parâmetros no teclado, ou última iluminação enviada pelo aplicativo no mouse. Não há cópia do estado original de fábrica. Desfazer começa a ficar disponível após uma alteração feita nesta versão.','sub'),False,False,0)
        box.pack_start(label('Sobre esta versão','section'),False,False,0)
        box.pack_start(label('Versão 0.4 · aplicativo comunitário independente. RGB do teclado baseado no protocolo Evision, adaptado ao CL-TK87. Mouse com codificação CL-MK043 identificada no software oficial. Sem atualização de firmware, captura de digitação ou serviço em segundo plano.','sub'),False,False,0)
        return scroll

    def values(self):
        k={'mode':self.k['mode'].get_active_text(),'color':color_value(self.k['color']),
           'brightness':int(self.k['brightness'].get_value()),'speed':int(self.k['speed'].get_value()),
           'direction':self.k['direction'].get_active(),'random':self.k['random'].get_active()}
        m={'mode':self.m['mode'].get_active_text(),'color':color_value(self.m['color']),'brightness':int(self.m['brightness'].get_value()),'speed':int(self.m['speed'].get_value())}
        return {'keyboard':k,'mouse':m}

    def validate(self,values):
        keyboard_packet(values['keyboard']);mouse_lighting_sequence({key:values['mouse'][key] for key in ('mode','color','brightness','speed') if key in values['mouse']})

    def populate(self,values):
        values=copy.deepcopy(values)
        values['mouse']={'brightness':255,'speed':2,**values['mouse']}
        for controls,kind in [(self.k,'keyboard'),(self.m,'mouse')]:
            for key,value in values[kind].items():
                if key not in controls:continue
                widget=controls[key]
                if key=='color':
                    c=Gdk.RGBA();c.parse(value);widget.set_rgba(c)
                elif key=='dpi':
                    for w,v in zip(widget,value):w.set_value(v)
                elif key=='buttons':
                    for w,v in zip(widget,value):set_combo(w,v)
                elif key=='active':widget.set_active(value)
                elif key=='direction':widget.set_active(value)
                elif key=='random':widget.set_active(value)
                elif isinstance(widget,Gtk.ComboBoxText):set_combo(widget,value)
                else:widget.set_value(value)
        for controls in (self.k,self.m):
            controls['hex'].set_text('Cor selecionada: '+color_value(controls['color']).upper()+' · escolher não aplica')
        self.kpreview.queue_draw();self.mpreview.queue_draw()

    def refresh(self):
        if self.busy:return True
        try:
            devices=backend.detect();lines=[]
            for kind,name,button in [('keyboard','CL-TK87',self.kapply),('mouse','MK043',self.mapply)]:
                dev=devices[kind]
                state='não encontrado' if not dev else ('conectado · acesso liberado' if dev['access'] else 'conectado · requer acesso USB')
                lines.append(f'{name}: {state}')
                enabled=bool(dev and dev['access'])
                button.set_sensitive(enabled);self.recovery[kind].set_sensitive(enabled)
                self.undo_buttons[kind].set_sensitive(enabled and backend.undo_available(kind))
            self.devices.set_text('   •   '.join(lines))
        except Exception as exc:self.devices.set_text(f'Falha de detecção: {exc}')
        return True

    def work(self,action):
        if self.busy:return
        self.busy=True;self.kapply.set_sensitive(False);self.mapply.set_sensitive(False)
        for button in [*self.recovery.values(),*self.undo_buttons.values()]:button.set_sensitive(False)
        self.status.set_text('Processando…')
        def worker():
            success=True
            try:message=action()
            except PermissionError:
                success=False;message='Sem permissão USB. Clique em Liberar acesso USB e tente novamente.'
            except Exception as exc:
                success=False;message=f'Não foi possível concluir: {exc}'
            GLib.idle_add(self.done,message,success)
        threading.Thread(target=worker,daemon=True).start()

    def done(self,message,success=True):
        self.busy=False
        kind=getattr(self,'_refresh_after_undo',None)
        self._refresh_after_undo=None
        if success and kind:
            try:
                values=self.values()
                saved=json.loads((backend.STATE/'last-applied.json').read_text())[kind]
                values[kind]=saved;self.populate(values)
            except (OSError,ValueError,KeyError,TypeError):pass
        self.status.set_text(message);self.refresh();return False

    def confirm_change(self,title,text):
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,text=title)
        dialog.format_secondary_text(text)
        answer=dialog.run();dialog.destroy();return answer==Gtk.ResponseType.OK

    def restore_blue(self,kind):
        if self.busy:return
        if not self.confirm_change('Voltar ao azul testado?',
            'Será aplicada apenas iluminação azul fixa neste dispositivo. Não é uma restauração de fábrica. No mouse, DPI e botões não são enviados.'):
            return
        values=self.values()
        if kind=='keyboard':
            values[kind].update(mode='Cor fixa',color='#0000ff',brightness=4,random=False)
        else:values[kind].update(mode='Cor fixa',color='#0000ff',brightness=255,speed=2)
        self.populate(values)
        self.work(lambda:(backend.apply_keyboard if kind=='keyboard' else backend.apply_mouse)(values[kind]))

    def undo(self,kind):
        if self.busy:return
        if not self.confirm_change('Desfazer a última iluminação?',
            'Restaura a cópia anterior salva nesta versão. No mouse, essa cópia é do último modo/cor enviado pelo aplicativo; não é o perfil original de fábrica.'):
            return
        self._refresh_after_undo=kind
        self.work(lambda:backend.undo_lighting(kind))

    def apply(self,kind):
        try:
            values=self.values()[kind]
            (keyboard_packet if kind=='keyboard' else mouse_lighting_sequence)(values)
        except Exception as exc:self.status.set_text(f'Confira os valores: {exc}');return
        self.work(lambda:(backend.apply_keyboard if kind=='keyboard' else backend.apply_mouse)(values))

    def permissions(self,*_):
        def action():
            result=subprocess.run(['pkexec','/bin/sh',str(ROOT/'permissoes.sh')],capture_output=True,text=True,timeout=180)
            if result.returncode:raise RuntimeError('Autenticação cancelada ou falha ao instalar regra USB.')
            return 'Regras instaladas. Se necessário, reconecte teclado/mouse e clique em Detectar.'
        self.work(action)

    def export_profile(self,*_):
        try:
            values=self.values();self.validate(values)
            dialog=Gtk.FileChooserDialog(title='Salvar perfil',parent=self,action=Gtk.FileChooserAction.SAVE)
            dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Salvar',Gtk.ResponseType.OK)
            dialog.set_current_name('meu-kit-clanm.json');dialog.set_do_overwrite_confirmation(True)
            if dialog.run()==Gtk.ResponseType.OK:
                backend.atomic_json(Path(dialog.get_filename()),{'version':1,'devices':values})
                self.status.set_text('Perfil salvo. Guarde esse JSON para depois de formatar.')
            dialog.destroy()
        except Exception as exc:self.status.set_text(f'Falha ao salvar: {exc}')

    def import_profile(self,*_):
        dialog=Gtk.FileChooserDialog(title='Carregar perfil',parent=self,action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Abrir',Gtk.ResponseType.OK)
        if dialog.run()==Gtk.ResponseType.OK:
            try:
                path=Path(dialog.get_filename())
                if path.stat().st_size>65536:raise ValueError('Arquivo muito grande.')
                profile=json.loads(path.read_text())
                if profile.get('version')!=1:raise ValueError('Versão de perfil incompatível.')
                self.validate(profile['devices']);self.populate(profile['devices'])
                self.status.set_text('Perfil carregado na tela. Clique em Aplicar no dispositivo desejado.')
            except Exception as exc:self.status.set_text(f'Perfil inválido: {exc}')
        dialog.destroy()

    def draw_preview(self,area,cr,kind):
        w=area.get_allocated_width();h=area.get_allocated_height()
        color=(self.k if kind=='keyboard' else self.m).get('color')
        c=color.get_rgba() if color else Gdk.RGBA(*rgb_token(self.theme,'accent'),1)
        cr.set_source_rgb(*rgb_token(self.theme,'input'));cr.paint()
        if kind=='keyboard':
            keyw=min((w-50)/22,29);x0=(w-keyw*22)/2
            for row in range(4):
                for col in range(22):
                    cr.rectangle(x0+col*keyw+1,8+row*23,keyw-4,18)
                    cr.set_source_rgba(c.red,c.green,c.blue,.28+row*.16);cr.fill_preserve()
                    cr.set_source_rgba(c.red,c.green,c.blue,.8);cr.set_line_width(1);cr.stroke()
        else:
            cr.save();cr.translate(w/2,h/2);cr.scale(43,47);cr.arc(0,0,1,0,6.284)
            cr.set_source_rgb(*rgb_token(self.theme,'surface'));cr.fill_preserve();cr.set_source_rgba(c.red,c.green,c.blue,1);cr.set_line_width(.06);cr.stroke();cr.restore()
            cr.set_source_rgba(c.red,c.green,c.blue,1);cr.rectangle(w/2-3,18,6,18);cr.fill()
        return False


def run(preview=None):
    window=Window();window.show_all()
    if preview:
        def capture():
            pix=Gdk.pixbuf_get_from_window(window.get_window(),0,0,window.get_allocated_width(),window.get_allocated_height())
            pix.savev(str(preview),'png',[],[]);Gtk.main_quit();return False
        GLib.timeout_add(500,capture)
    Gtk.main()
