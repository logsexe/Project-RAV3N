from __future__ import annotations

import time

from textual.binding import Binding
from textual.widgets import Input, Static

from fieldos.app_v05 import CATEGORIES, OperatorPane
from fieldos.app_v11 import FieldOSApp as BaseFieldOSApp

NAV_ITEMS = (("DASHBOARD","Operational overview"),("TOOLS","Command and recipe library"),("PLAYBOOKS","Guided field workflows"),("OPERATIONS","Cases and field sessions"),("ASSETS","Tracked investigation entities"),("EVIDENCE","Collected and verified artefacts"),("INTEL","Timeline and intelligence state"),("KNOWLEDGE","Offline reference library"),("TERMINAL","Operator shell sessions"),("HARDWARE","RVN-01 system telemetry"),("SETTINGS","Profile and visual controls"))

class FieldOSApp(BaseFieldOSApp):
    TITLE="RAVEN // FIELD//OS V1.2"
    CSS="""Screen { background: #030607; color: #d7ddd9; } #shell { height: 1fr; padding: 0 1; } #status { height: 1; color: #d7ddd9; background: #0b1214; text-style: bold; } #breadcrumb { height: 1; color: #66787c; } #title { height: 2; color: #ffffff; text-style: bold; padding-top: 1; } #description { height: 2; color: #839398; } #body { height: 1fr; padding: 1 2; border: solid #26393d; background: #060b0d; } #body:focus { border: heavy #b7c9c8; background: #091113; } #example { height: 2; color: #8b999c; padding: 0 1; } #search, #entry, #command { height: 3; border: tall #40575b; background: #071012; } #search:focus, #entry:focus, #command:focus { border: tall #d7ddd9; } #terminal-tabs { height: 1; color: #d7ddd9; text-style: bold; } #terminal-output { height: 1fr; padding: 0 1; border: solid #26393d; background: #010304; } #footer { height: 1; color: #a8b9bb; background: #0b1214; text-align: center; } .hidden { display: none; }"""
    BINDINGS=[Binding("up","move_up",show=False,priority=True),Binding("down","move_down",show=False,priority=True),Binding("right","open",show=False,priority=True),Binding("enter","open",show=False,priority=True),Binding("left","back",show=False,priority=True),Binding("escape","back",show=False,priority=True),Binding("/","search",show=False),Binding("f1","help","Help"),Binding("f2","terminal","Terminal"),Binding("f3","sessions","Operations"),Binding("f4","status","Hardware"),Binding("f5","notes","Notes"),Binding("f9","playbooks","Playbooks"),Binding("f10","theme","Theme"),Binding("f11","profile","Profile"),Binding("f12","intelligence","Intel"),Binding("ctrl+c","interrupt","Interrupt",show=False),Binding("ctrl+q","quit","Quit")]
    def __init__(self): super().__init__(); self.nav_index=0; self.settings_index=0; self._airgap_cache=None; self._airgap_checked_at=0.0
    def _airgap_state(self):
        now=time.monotonic()
        if self._airgap_cache is None or now-self._airgap_checked_at>=5.0: self._airgap_cache=self.airgap.status(); self._airgap_checked_at=now
        return self._airgap_cache
    def refresh_status(self):
        t=self.telemetry_provider.read(); a=self._airgap_state(); battery="EXT" if t.battery_percent<0 else f"{t.battery_percent}%"; self.query_one("#status",Static).update(f"RAVEN // FIELD//OS V1.2   {self.operations.active.id:<12}   {self.profiles.current.name:<9}   {'AIRGAP' if a.active else 'ONLINE':<7}   BAT {battery}")
    @staticmethod
    def _telemetry_flag(v): return "--" if str(v).upper() in {"OFF","NOT PRESENT","DISCONNECTED","UNKNOWN","NO FIX"} else "OK"
    def render_home(self):
        self.view="home"; self.hide_aux(); t=self.telemetry_provider.read(); a=self._airgap_state(); op=self.operations.active.id; assets=len(self.intelligence.list_assets(op)); ev=len(self.intelligence.list_evidence(op)); events=len(self.intelligence.timeline(op,limit=999)); temp="--" if t.cpu_temp_c<0 else f"{t.cpu_temp_c:.1f}C"; nav=[f"{'> ' if i==self.nav_index else '  '}{n:<12}" for i,(n,_) in enumerate(NAV_ITEMS)]; stat=["CURRENT OPERATION",op,"",f"ASSETS      {assets:>3}",f"EVIDENCE    {ev:>3}",f"EVENTS      {events:>3}","",f"NETWORK     {self._telemetry_flag(t.network):>3}",f"GPS         {self._telemetry_flag(t.gps):>3}",f"MESH        {self._telemetry_flag(t.mesh):>3}",f"CPU         {temp:>7}",f"ISOLATION   {'ON' if a.active else 'OFF':>3}"]; lines=["OPERATOR MENU                     RVN-01 STATUS","--------------------------------  ----------------------"]
        for i in range(max(len(nav),len(stat))): lines.append(f"{nav[i] if i<len(nav) else '':<34}{stat[i] if i<len(stat) else ''}")
        self.query_one("#body",OperatorPane).update("\n".join(lines)); self.set_header("FIELD//OS > DASHBOARD","RAVEN // FIELD OPERATIONS TERMINAL",f"PROFILE {self.profiles.current.name} // {self.operations.active.name}","↑↓ SELECT  ENTER OPEN  / SEARCH  ESC BACK  CTRL+Q EXIT"); self.focus_body()
    def render_tools_home(self):
        self.view="tools-home"; self.hide_aux(); lines=[]
        for i,(n,d) in enumerate(CATEGORIES): lines.append(f"{'> ' if i==self.category_index else '  '}{n:<12} {d:<34} {len(self.profiles.filter_tools(self.tools.for_category(n.lower()))):02d}")
        self.query_one("#body",OperatorPane).update("\n".join(lines)); self.set_header("FIELD//OS > TOOLS","COMMAND // RECIPE LIBRARY",f"PROFILE FILTER // {self.profiles.current.name}","ESC BACK  ↑↓ CATEGORY  ENTER OPEN  / SEARCH"); self.focus_body()
    def render_library(self):
        self.view="library"; self.hide_aux(); cat,desc=CATEGORIES[self.category_index]; self.active_tools=list(self.profiles.filter_tools(self.tools.for_category(cat.lower()))); self.tool_index=min(self.tool_index,max(0,len(self.active_tools)-1)); lines=[]
        for i,t in enumerate(self.active_tools): lines.append(f"{'> ' if i==self.tool_index else '  '}{'*' if self.state.is_favourite(t.id) else ' '} {t.name[:25]:<25} {'READY' if t.installed else '----':<5} {(t.subcategory or 'general').upper()[:24]}")
        self.query_one("#body",OperatorPane).update("\n".join(lines) if lines else "NO TOOLS AVAILABLE IN CURRENT PROFILE"); self.set_header(f"FIELD//OS > TOOLS > {cat}",f"{cat} // LIBRARY",desc,"ESC BACK  ↑↓ SELECT  ENTER DETAILS  / SEARCH"); self.focus_body()
    def render_tool(self):
        if not self.active_tools:return
        self.view="tool"; self.hide_aux(); t=self.active_tools[self.tool_index]; self.state.record_recent(t.id); r=t.recipes[self.recipe_index] if t.recipes else None; lines=[f"TOOL         {t.name}",f"CATEGORY     {t.category.upper()} / {(t.subcategory or 'GENERAL').upper()}",f"STATUS       {'INSTALLED' if t.installed else 'NOT INSTALLED'}",f"PRIORITY     {t.priority.upper()}",f"MODE         {'AUTHORISED USE' if t.authorised_use_only else 'STANDARD'}","","DESCRIPTION",t.description or "FIELD//OS indexed tool","","RECIPES"]
        if t.recipes:
            for i,x in enumerate(t.recipes): lines.append(f"{'> ' if i==self.recipe_index else '  '}{x.name}")
            lines.extend(["","STAGED COMMAND",f"$ {r.command}"])
        elif t.command: lines.extend(["> BASE COMMAND","","STAGED COMMAND",f"$ {t.command}"])
        else: lines.append("NO COMMAND RECIPE INDEXED")
        self.query_one("#body",OperatorPane).update("\n".join(lines)); self.set_header(f"FIELD//OS > {t.category.upper()} > {t.name.upper()}",t.name.upper(),"Review command before execution; operation capture remains enabled","ESC BACK  ↑↓ RECIPE  ENTER STAGE  F FAVOURITE  F2 TERMINAL"); self.focus_body()
    def render_assets(self):
        self.view="assets"; self.hide_aux(); x=self.intelligence.list_assets(self.operations.active.id); lines=["ID           TYPE         VALUE","------------ ------------ ------------------------------------------"]+[f"{i.id:<12} {i.kind[:12]:<12} {i.value}" for i in x[:18]]; lines+=[] if x else ["NO ASSETS RECORDED FOR THIS OPERATION"]; self.query_one("#body",OperatorPane).update("\n".join(lines)); self.set_header("FIELD//OS > ASSETS","ASSET ENGINE",f"{len(x)} tracked entities // {self.operations.active.id}","ESC BACK  / SEARCH  fieldos-control asset add ..."); self.focus_body()
    def render_evidence(self):
        self.view="evidence"; self.hide_aux(); x=self.intelligence.list_evidence(self.operations.active.id); lines=["ID           SHA256       MODE  SOURCE","------------ ------------ ----- ------------------------------------"]+[f"{i.id:<12} {i.sha256[:12]} {'ENC' if i.encrypted else 'RAW':<5} {i.source_name}" for i in x[:18]]; lines+=[] if x else ["NO EVIDENCE RECORDED FOR THIS OPERATION"]; self.query_one("#body",OperatorPane).update("\n".join(lines)); self.set_header("FIELD//OS > EVIDENCE","EVIDENCE ENGINE",f"{len(x)} artefacts // SHA256 tracked","ESC BACK  fieldos-control evidence ingest ..."); self.focus_body()
    def render_settings(self):
        self.view="settings"; self.hide_aux(); a=self._airgap_state(); rows=[("PROFILE",self.profiles.current.name,"ENTER cycles operational profile"),("THEME",self.themes.current.name,"ENTER cycles low-light theme"),("AIRGAP","ACTIVE" if a.active else "OFF","Use fieldos-control airgap on --confirm")]; self.query_one("#body",OperatorPane).update("\n".join(f"{'> ' if i==self.settings_index else '  '}{n:<10} {v:<18} {d}" for i,(n,v,d) in enumerate(rows))); self.set_header("FIELD//OS > SETTINGS","OPERATOR SETTINGS","Local profile, appearance and isolation state","ESC BACK  ↑↓ SELECT  ENTER CHANGE"); self.focus_body()
    def action_move_up(self):
        if self.view=="home": self.nav_index=max(0,self.nav_index-1); self.render_home()
        elif self.view=="tools-home": self.category_index=max(0,self.category_index-1); self.render_tools_home()
        elif self.view=="settings": self.settings_index=max(0,self.settings_index-1); self.render_settings()
        else: super().action_move_up()
    def action_move_down(self):
        if self.view=="home": self.nav_index=min(len(NAV_ITEMS)-1,self.nav_index+1); self.render_home()
        elif self.view=="tools-home": self.category_index=min(len(CATEGORIES)-1,self.category_index+1); self.render_tools_home()
        elif self.view=="settings": self.settings_index=min(2,self.settings_index+1); self.render_settings()
        else: super().action_move_down()
    def action_open(self):
        if isinstance(self.focused,Input):return
        if self.view=="home":
            c=NAV_ITEMS[self.nav_index][0]
            if c=="DASHBOARD":self.render_home()
            elif c=="TOOLS":self.render_tools_home()
            elif c=="PLAYBOOKS":self.action_playbooks()
            elif c=="OPERATIONS":self.action_sessions()
            elif c=="ASSETS":self.render_assets()
            elif c=="EVIDENCE":self.render_evidence()
            elif c=="INTEL":self.action_intelligence()
            elif c=="KNOWLEDGE":self.render_knowledge()
            elif c=="TERMINAL":self.action_terminal()
            elif c=="HARDWARE":self.action_status()
            elif c=="SETTINGS":self.render_settings()
            return
        if self.view=="tools-home":self.tool_index=0;self.recipe_index=0;self.render_library();return
        if self.view=="settings":
            if self.settings_index==0:self.action_profile();self.render_settings()
            elif self.settings_index==1:self.action_theme();self.render_settings()
            return
        super().action_open()
    def action_back(self):
        if isinstance(self.focused,Input): super().action_back(); return
        if self.view=="library": self.render_tools_home()
        elif self.view=="tools-home": self.render_home()
        elif self.view in {"assets","evidence","settings","playbooks","intelligence","status","sessions","knowledge","notes"}: self.render_home()
        elif self.view=="playbook": self.action_playbooks()
        elif self.view=="tool": self.render_library()
        else: super().action_back()
    def open_tool(self,tool):
        for i,(n,_) in enumerate(CATEGORIES):
            if n.lower()==tool.category.lower():self.category_index=i;break
        self.active_tools=list(self.profiles.filter_tools(self.tools.for_category(tool.category))); self.tool_index=next((i for i,x in enumerate(self.active_tools) if x.id==tool.id),0); self.recipe_index=0; self.render_tool()
    def render_search_results(self,query):
        tm=[t for t in self.tools.search(query) if self.profiles.allows_tool(t)]; km=self.knowledge.search(query); q=query.lower(); am=[x for x in self.intelligence.list_assets(self.operations.active.id) if q in x.value.lower() or q in x.kind.lower() or q in (x.label or "").lower()]; self.search_results=[("tool",x) for x in tm[:16]]+[("knowledge",x) for x in km[:12]]+[("asset",x) for x in am[:12]]; self.search_index=min(self.search_index,max(0,len(self.search_results)-1)); lines=[]
        for i,(k,x) in enumerate(self.search_results): lines.append(f"{'> ' if i==self.search_index else '  '}{'TOOL   '+x.name[:28]+' '+x.category.upper() if k=='tool' else 'KNOW   '+x.title[:28]+' '+x.category.upper() if k=='knowledge' else 'ASSET  '+x.value[:28]+' '+x.kind.upper()}")
        self.query_one("#body",OperatorPane).update("\n".join(lines) if lines else "NO MATCHES"); self.set_header("FIELD//OS > SEARCH",f'SEARCH // "{query.upper()}"',f"{len(self.search_results)} combined result(s)","↑↓ SELECT  ENTER OPEN  ESC BACK"); self.focus_body()
    def action_help(self):
        if self.view!="help":self.return_view=self.view
        self.view="help";self.hide_aux();self.query_one("#body",OperatorPane).update("PRIMARY CONTROL\n↑ ↓        Navigate menu / list\nENTER      Open / select / stage\nESC        Back\n/          Global search\n\nFAST ACCESS\nF2         Terminal\nF3         Operations\nF4         Hardware status\nF5         Operation notes\nF9         Playbooks\nF10        Theme\nF11        Profile\nF12        Intelligence\nCTRL+Q     Exit FIELD//OS\n\nCommands remain review-first and completed commands are captured under the active operation.");self.set_header("FIELD//OS > HELP","OPERATOR CONTROL","Keyboard-first controls for RVN-01","ESC BACK");self.focus_body()
