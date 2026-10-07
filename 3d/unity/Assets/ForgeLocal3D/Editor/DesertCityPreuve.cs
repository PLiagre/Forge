using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using ForgeLocal3D.Captures;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Contrôle du lot 386, en Play : Unity joue les gestes de la preuve et redessine la même ville. Trois
    // sessions, chacune un lancement d'Unity sur la première implantation de la sélection, sur la mécanique de
    // DesertCityBatiments (recopiée, clés de session à elle) : `Jouer` (service neuf) trace la route de plaine,
    // découpe une parcelle et y pose une scierie, chaque geste par ce que `Update` appelle pour sa touche, puis
    // fait passer sept ticks et relève la ville ; `Relancer` (même service) rouvre la ville et doit retrouver ce
    // relevé ; `Vierge` (service neuf) ne doit rien dessiner. Tout dépôt est celui de l'outil. Les étapes des
    // bâtiments se calculent ici, d'après les nombres du plan, sans passer par la vue. Rien n'est capturé.
    [InitializeOnLoad] public static class DesertCityPreuve
    {
        const string Flag="Forge.Desert.Preuve",Cle="Forge.Desert.Preuve.Session",Id="Forge.Desert.Preuve.Implantation";
        const string Output=DesertRoads.Sorties;
        const int TICKS_APRES=7;
        static int last=-1,settle;
        static readonly string Vide=Hacher("");
        static readonly string[] TYPES={"tracer_route","decouper_parcelle","poser_batiment"};

        [Serializable] class Selection{public string[] implantations;}
        [Serializable] class Consigne{public bool ville_locale;}
        [Serializable] public class Trace{public long identifiant=-1;public string nature="",etat="";}
        [Serializable] public class Geste{public string type="";public long apres_le_tick=-1,identifiant=-1;}
        [Serializable] public class Releve
        {
            public long tick=-1;public long[] rues=new long[0],rues_posees=new long[0];
            public Trace[] parcelles=new Trace[0],parcelles_plan=new Trace[0],batiments=new Trace[0],batiments_plan=new Trace[0];
            public int pieces_parcelles=-1,pieces_batiments=-1;
            public string empreinte_rues="",empreinte_parcelles="",empreinte_batiments="",empreinte="";
        }
        [Serializable] public class Rapport
        {
            public string session="",implantation="";public long cell=-1;public int port=-1;public long tick_ouverture=-1;public bool ville_locale;
            public Geste[] gestes=new Geste[0];public Releve ouverture=new Releve(),ville=new Releve();public string vierge="";public string[] defauts=new string[0];
        }

        static DesertCityPreuve(){EditorApplication.update+=Tick;}

        public static void Jouer()=>Lancer("jouer");
        public static void Relancer()=>Lancer("relance");
        public static void Vierge()=>Lancer("vierge");

        static void Lancer(string session)
        {
            var selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
            if(selection?.implantations==null||selection.implantations.Length==0)
                throw new InvalidOperationException("Aucune implantation : lancer py local3d/atelier_desert.py preuve");
            string id=selection.implantations[0];
            SessionState.SetString(Cle,session);SessionState.SetString(Id,id);
            EditorSceneManager.OpenScene(ScenePath(id));
            SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static string ScenePath(string id)=>DesertBuilder.Root+"/Scenes/Forge_Desert_Ville_"+id+".unity";
        static string Dossier(string id)=>Output+id+"/preuve/";
        static string Chemin(string id,string session)=>Dossier(id)+session+".json";

        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            // Deux images pour que les composants de la scène aient fait leur Awake et leur Start : l'outil a ouvert la ville.
            if(settle++<2)return;
            SessionState.SetBool(Flag,false);
            string session=SessionState.GetString(Cle,""),id=SessionState.GetString(Id,"");
            var report=new Rapport{session=session,implantation=id};var faults=new List<string>();
            try
            {
                if(SceneManager.GetActiveScene().name!="Forge_Desert_Ville_"+id)
                    throw new InvalidOperationException("scène active "+SceneManager.GetActiveScene().name+" au lieu de Forge_Desert_Ville_"+id);
                Run(report,faults);
            }
            // Une exception hors des étapes (une lecture du plan, par exemple) est un défaut : le rapport est écrit quand même.
            catch(Exception e){Debug.LogException(e);faults.Add(session+" : exception : "+e.GetBaseException().Message);}
            report.defauts=faults.ToArray();
            try
            {
                Directory.CreateDirectory(Dossier(id));
                File.WriteAllText(Chemin(id,session),JsonUtility.ToJson(report,true));
                Debug.Log("DESERT_PREUVE "+session+" "+id+" "+string.Join(" | ",report.defauts));
                CitadelEditorBridge.Finish(report.defauts.Length==0?0:1);
            }
            catch(Exception e){Debug.LogException(e);CitadelEditorBridge.Finish(1);}
        }

        static string N(long v)=>v.ToString(CultureInfo.InvariantCulture);
        static string Hacher(string texte)
        {
            using var sha=SHA256.Create();
            return string.Concat(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(texte)).Select(b=>b.ToString("x2")));
        }
        static string Liste(IEnumerable<long> ids)=>"["+string.Join(", ",ids.Select(N))+"]";
        static string Etats(IEnumerable<Trace> t)=>"["+string.Join(", ",t.Select(x=>N(x.identifiant)+(x.nature.Length>0?" "+x.nature:"")+" "+x.etat))+"]";
        static bool Memes(Trace[] a,Trace[] b)=>a.Select(x=>(x.identifiant,x.nature,x.etat)).SequenceEqual(b.Select(x=>(x.identifiant,x.nature,x.etat)));

        static void Run(Rapport report,List<string> faults)
        {
            var tool=Object.FindFirstObjectByType<DesertRoadTool>();
            if(!tool||!tool.roads)throw new InvalidOperationException("Scène sans outil des routes : relancer py local3d/atelier_desert.py terrain");
            var roads=tool.roads;var gestes=DesertRoads.Lire(report.implantation);
            tool.automatique=true;
            report.cell=tool.Cellule;report.port=tool.Port;report.tick_ouverture=tool.TickOuverture;
            string consigne=Dossier(report.implantation)+"consigne.json";
            if(!File.Exists(consigne))faults.Add(report.session+" : consigne absente ("+consigne+") : lancer py local3d/atelier_desert.py preuve");
            else report.ville_locale=JsonUtility.FromJson<Consigne>(File.ReadAllText(consigne)).ville_locale;
            if(report.tick_ouverture<0)faults.Add(report.session+", tick -1 : l'outil n'a pas lu de plan à l'ouverture : "+tool.Message);
            report.ouverture=Relever(tool,Acceptees(tool.Ouverture));
            if(report.ouverture.tick!=tool.TickOuverture)
                faults.Add(report.session+", tick "+N(report.ouverture.tick)+" : le plan relu n'est pas celui que l'outil a dessiné à l'ouverture (tick "+N(tool.TickOuverture)+")");
            long tickAtelier=-1;
            if(report.session=="jouer")tickAtelier=Gestes(tool,gestes,report,faults);
            else report.ville=report.ouverture;
            // Le sable vierge, après le relevé de la ville ; puis le terrain de la scène.
            roads.Preparer(gestes.parametres,gestes.graine);report.vierge=roads.Empreintes().Tout;
            roads.Restaurer();

            JugerReleve(report.session,report.ouverture,faults);
            if(report.session=="jouer"){if(report.ville.tick>=0)JugerReleve(report.session,report.ville,faults);JugerJouer(report,tickAtelier,faults);}
            else
            {
                string chemin=Chemin(report.implantation,"jouer");
                var jouer=File.Exists(chemin)?JsonUtility.FromJson<Rapport>(File.ReadAllText(chemin)):null;
                if(report.session=="relance")
                {
                    if(jouer==null)faults.Add("relance, tick "+N(report.ville.tick)+" : rapport de la session jouer absent : "+chemin);
                    else JugerRelance(report,jouer,faults);
                }
                else JugerVierge(report,tool,jouer,faults);
            }
        }

        static long[] Acceptees(IEnumerable<(long identifiant,DesertRoads.Resultat resultat)> essais)=>essais.Where(e=>e.resultat.acceptee).Select(e=>e.identifiant).ToArray();

        // La ville telle que l'outil l'a dessinée en dernier, et le plan relu maintenant.
        static Releve Relever(DesertRoadTool tool,long[] posees)
        {
            var plan=Lot362.Lire(tool.Port,tool.Cellule);
            var natures=plan.Batiments.ToDictionary(b=>b.Identifiant,b=>b.Nature);
            var r=new Releve{tick=plan.Tick,rues=plan.Rues.Select(u=>u.Identifiant).ToArray(),rues_posees=posees,
                parcelles=tool.Parcelles.Select(p=>new Trace{identifiant=p.identifiant,etat=p.etat}).ToArray(),
                parcelles_plan=plan.Parcelles.Select(p=>new Trace{identifiant=p.Identifiant,etat=p.EnChantier?"cordeau":"bornes"}).ToArray(),
                batiments=tool.Batiments.Select(b=>new Trace{identifiant=b.identifiant,nature=natures.TryGetValue(b.identifiant,out var n)?n:"",etat=b.etat}).ToArray(),
                // Calculée ici d'après les nombres du plan, comme DesertCityBatiments.Relever : une étape mal lue par la vue doit se voir.
                batiments_plan=plan.Batiments.Select(b=>new Trace{identifiant=b.Identifiant,nature=b.Nature,etat=!b.EnChantier?"fini":2*b.TravailFourni<b.TravailRequis?"piquets":"murs"}).ToArray(),
                pieces_parcelles=tool.RacineParcelles?tool.RacineParcelles.childCount:-1,pieces_batiments=tool.RacineBatiments?tool.RacineBatiments.childCount:-1,
                empreinte_rues=tool.roads.Empreintes().Tout,empreinte_parcelles=tool.EmpreinteParcelles,empreinte_batiments=tool.EmpreinteBatiments};
            r.empreinte=Hacher(r.empreinte_rues+"\n"+r.empreinte_parcelles+"\n"+r.empreinte_batiments);
            return r;
        }

        // Une étape de la session jouer : une exception, ou un manque qu'elle rend, devient un défaut qui la nomme.
        sealed class Etapes
        {
            public readonly List<string> faults;public long tick;
            public Etapes(List<string> f,long t){faults=f;tick=t;}
            public bool Jouer(string nom,Func<string> etape)
            {
                string manque;
                try{manque=etape();}
                catch(Exception e){Debug.LogException(e);manque="exception : "+e.GetBaseException().Message;}
                if(manque!=null)faults.Add("jouer, tick "+N(tick)+", "+nom+" : "+manque);
                return manque==null;
            }
        }

        // Service neuf : la route, la parcelle et l'atelier par l'outil du joueur, puis le temps. Rend le tick du plan
        // après l'atelier, -1 si la session s'est arrêtée avant.
        static long Gestes(DesertRoadTool tool,DesertRoads.Gestes gestes,Rapport report,List<string> faults)
        {
            int port=tool.Port;long cell=tool.Cellule;var terrain=tool.roads.terrain;var camera=tool.view;
            var ville=camera?camera.GetComponent<DesertCityCamera>():null;
            var e=new Etapes(faults,report.ouverture.tick);var faits=new List<Geste>();long tickAtelier=-1;
            PlanLu Plan(){var p=Lot362.Lire(port,cell);e.tick=p.Tick;return p;}
            string Recu(string quoi)=>tool.Recu==null?quoi+" sans reçu du monde : "+tool.Message:!tool.Recu.Acceptee?quoi+" refusé(e) par le monde : "+tool.Message:null;
            RueDuPlan rue=null;ParcelleDuPlan parcelle=null;

            bool ok=e.Jouer("la route",()=>
            {
                if(!ville)return "la caméra de l'outil n'a pas de DesertCityCamera";
                var g=gestes.routes.FirstOrDefault(x=>x.famille=="plaine");
                if(g==null)return "jeu de gestes sans route plaine";
                var avant=Plan().Rues.Select(u=>u.Identifiant).ToArray();
                // Les clics à l'écran, vus de haut, sur une image de la taille de la photo (comme Lot293.Depot).
                int q=g.x.Length/2;var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
                bool clique=true;DesertRoads.Resultat essai=null;
                try
                {
                    ville.Poser(Lot362.Monde(terrain,g.x[q],g.y[q]),ville.Cap,85f,160f);
                    tool.largeur=g.largeur;tool.Annuler();
                    for(int i=0;i<g.x.Length;i++)clique&=tool.Clic(camera.WorldToScreenPoint(Lot362.Monde(terrain,g.x[i],g.y[i])));
                    if(clique)essai=tool.Valider();
                }
                finally{camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);}
                if(!clique)return "un point de la route "+g.id+" n'a pas été cliqué sur le terrain : "+tool.Message;
                if(essai==null||!essai.acceptee)return "la route "+g.id+" refusée à l'essai du relief : "+tool.Message;
                var manque=Recu("la route "+g.id);if(manque!=null)return manque;
                var geste=new Geste{type=TYPES[0],apres_le_tick=tool.Recu.AppliqueeAuTick.Value};faits.Add(geste);
                Lot362.Tick(port);
                if(!tool.Attendre())return "après le tick, l'outil n'a pas relu de plan plus récent que son dépôt";
                var plan=Plan();var neuves=plan.Rues.Where(u=>!avant.Contains(u.Identifiant)).ToArray();
                if(neuves.Length!=1)return "le plan compte "+neuves.Length+" rue(s) de plus "+Liste(plan.Rues.Select(u=>u.Identifiant))+", il en faut une";
                rue=neuves[0];geste.identifiant=rue.Identifiant;
                if(!tool.Posees.Any(p=>p.identifiant==rue.Identifiant&&p.resultat.acceptee))
                    return "la rue "+N(rue.Identifiant)+" n'est pas posée par l'outil : "+tool.Message;
                return null;
            });

            ok=ok&&e.Jouer("la parcelle",()=>
            {
                if(rue.Points.Count<7)return "la rue "+N(rue.Identifiant)+" n'a que "+rue.Points.Count+" point(s), il faut un segment 5";
                var avant=Plan().Parcelles.Select(p=>p.Identifiant).ToArray();
                tool.EntrerParcelle();
                Lot375.Cliquer(camera,ville,tool,Lot375.Milieu(terrain,rue,5),Lot375.Point(rue,5,1,3),Lot375.Point(rue,5,9,17));
                var tracee=tool.ValiderParcelle();
                if(tracee==null||tool.Tracee==null||!tool.Tracee.Presente)return "l'outil n'a pas tracé la parcelle : "+tool.Message;
                var manque=Recu("la parcelle");if(manque!=null)return manque;
                var geste=new Geste{type=TYPES[1],apres_le_tick=tool.Recu.AppliqueeAuTick.Value};faits.Add(geste);
                Lot362.Tick(port);
                if(!tool.Attendre())return "après le tick, l'outil n'a pas relu de plan plus récent que son dépôt";
                var plan=Plan();var neuves=plan.Parcelles.Where(p=>!avant.Contains(p.Identifiant)).ToArray();
                if(neuves.Length!=1)return "le plan compte "+neuves.Length+" parcelle(s) de plus, il en faut une";
                parcelle=neuves[0];geste.identifiant=parcelle.Identifiant;
                var dessin=tool.Parcelles.Where(p=>p.identifiant==parcelle.Identifiant).ToArray();
                if(dessin.Length!=1||dessin[0].etat!="cordeau")
                    return "la parcelle "+N(parcelle.Identifiant)+" n'est pas dessinée au cordeau : "+string.Join(", ",tool.Parcelles.Select(p=>N(p.identifiant)+" "+p.etat+(string.IsNullOrEmpty(p.message)?"":" ("+p.message+")")));
                return null;
            });

            ok=ok&&e.Jouer("l'atelier",()=>
            {
                if(parcelle.Contour.Count==0)return "la parcelle "+N(parcelle.Identifiant)+" n'a pas de contour";
                var avant=Plan().Batiments.Select(b=>b.Identifiant).ToArray();
                var c=(x:parcelle.Contour.Average(k=>k.X),y:parcelle.Contour.Average(k=>k.Y));
                tool.EntrerBatiment(PoseDeBatiment.Natures[1]);
                Lot375.Cliquer(camera,ville,tool,Lot375.Milieu(terrain,rue,5),c);
                if(tool.Pose==null||!tool.Pose.Presente||tool.Pose.Nature!="scierie"||tool.Pose.Parcelle!=parcelle.Identifiant)
                    return "le clic au centre de la parcelle "+N(parcelle.Identifiant)+" ne forme pas une scierie sur elle : "+tool.Message;
                var manque=Recu("la scierie");if(manque!=null)return manque;
                var geste=new Geste{type=TYPES[2],apres_le_tick=tool.Recu.AppliqueeAuTick.Value};faits.Add(geste);
                Lot362.Tick(port);
                if(!tool.Attendre())return "après le tick, l'outil n'a pas relu de plan plus récent que son dépôt";
                var plan=Plan();var neufs=plan.Batiments.Where(b=>!avant.Contains(b.Identifiant)).ToArray();
                if(neufs.Length!=1)return "le plan compte "+neufs.Length+" bâtiment(s) de plus, il en faut un";
                var b=neufs[0];geste.identifiant=b.Identifiant;
                if(b.Nature!="scierie"||b.Parcelle!=parcelle.Identifiant)
                    return "le bâtiment "+N(b.Identifiant)+" est "+b.Nature+" sur la parcelle "+N(b.Parcelle)+", il faut une scierie sur la parcelle "+N(parcelle.Identifiant);
                var dessin=tool.Batiments.Where(x=>x.identifiant==b.Identifiant).ToArray();
                if(dessin.Length!=1||dessin[0].etat!="piquets")
                    return "le bâtiment "+N(b.Identifiant)+" n'est pas dessiné aux piquets : "+string.Join(", ",tool.Batiments.Select(x=>N(x.identifiant)+" "+x.etat+(string.IsNullOrEmpty(x.message)?"":" ("+x.message+")")));
                tickAtelier=plan.Tick;
                return null;
            });

            ok=ok&&e.Jouer("le temps",()=>
            {
                for(int k=0;k<TICKS_APRES;k++)Lot362.Tick(port);
                e.tick=tickAtelier+TICKS_APRES;
                return tool.Rafraichir()?null:"l'outil n'a pas redessiné la ville d'après le plan : "+tool.Message;
            });

            // La contre-épreuve : une rue posée par Unity seul, sans dépôt ni essai. Elle ne doit jamais passer à vide.
            ok=ok&&(!report.ville_locale||e.Jouer("la ville locale",()=>
            {
                var g=gestes.routes.FirstOrDefault(x=>x.famille=="flanc");
                if(g==null)return "jeu de gestes sans route flanc";
                var r=tool.roads.Poser(g);
                return r.acceptee?null:"la route "+g.id+" (flanc) refusée par le relief : "+r.message;
            }));

            report.gestes=faits.ToArray();
            if(ok)e.Jouer("le relevé",()=>{report.ville=Relever(tool,Acceptees(tool.Posees));return null;});
            return tickAtelier;
        }

        // Partout : la ville dessinée est celle du plan relu (identifiants, natures, états, ordre).
        static void JugerReleve(string session,Releve r,List<string> faults)
        {
            string t=session+", tick "+N(r.tick)+" : ";
            if(!Memes(r.parcelles,r.parcelles_plan))faults.Add(t+"parcelles dessinées "+Etats(r.parcelles)+" différentes du plan "+Etats(r.parcelles_plan));
            if(!Memes(r.batiments,r.batiments_plan))faults.Add(t+"bâtiments dessinés "+Etats(r.batiments)+" différents du plan "+Etats(r.batiments_plan));
        }

        static void JugerJouer(Rapport r,long tickAtelier,List<string> faults)
        {
            var o=r.ouverture;string t="jouer, tick "+N(o.tick)+" : ";
            if(o.rues.Length>0||o.parcelles_plan.Length>0||o.batiments_plan.Length>0||o.pieces_parcelles!=0||o.pieces_batiments!=0)
                faults.Add(t+"le service n'est pas neuf : "+o.rues.Length+" rue(s), "+o.parcelles_plan.Length+" parcelle(s) et "+o.batiments_plan.Length
                    +" bâtiment(s) au plan, "+o.pieces_parcelles+" et "+o.pieces_batiments+" pièce(s) à l'ouverture");
            if(o.empreinte_rues!=r.vierge)faults.Add(t+"le service n'est pas neuf : l'empreinte des rues à l'ouverture n'est pas celle du sable vierge");
            var types=r.gestes.Select(g=>g.type).ToArray();
            if(!types.SequenceEqual(TYPES))faults.Add(t+"gestes ["+string.Join(", ",types)+"] au lieu de ["+string.Join(", ",TYPES)+"]");
            var v=r.ville;
            if(v.tick<0){faults.Add("jouer, tick "+N(tickAtelier)+" : la ville n'a pas été relevée");return;}
            t="jouer, tick "+N(v.tick)+" : ";
            if(tickAtelier<0)faults.Add(t+"l'atelier n'a pas été posé : pas de tick à comparer");
            else if(v.tick!=tickAtelier+TICKS_APRES)faults.Add(t+"la ville est relevée au tick "+N(v.tick)+" au lieu de "+N(tickAtelier+TICKS_APRES)+" ("+N(tickAtelier)+" + "+TICKS_APRES+")");
            if(v.rues.Length!=1||!v.rues_posees.SequenceEqual(v.rues))
                faults.Add(t+"rues au plan "+Liste(v.rues)+", posées par l'outil "+Liste(v.rues_posees)+" : il faut une même rue");
            if(v.parcelles_plan.Length!=1||v.parcelles_plan[0].etat!="bornes")faults.Add(t+"parcelles au plan "+Etats(v.parcelles_plan)+" : il en faut une aux bornes");
            if(v.batiments_plan.Length!=1||v.batiments_plan[0].nature!="scierie"||v.batiments_plan[0].etat!="piquets")
                faults.Add(t+"bâtiments au plan "+Etats(v.batiments_plan)+" : il faut une scierie aux piquets");
            if(v.pieces_parcelles!=1||v.pieces_batiments!=1)
                faults.Add(t+v.pieces_parcelles+" pièce(s) sous la racine des parcelles et "+v.pieces_batiments+" sous celle des bâtiments, il en faut 1 et 1");
            if(v.empreinte_rues==r.vierge)faults.Add(t+"l'empreinte des rues est celle du sable vierge");
            if(v.empreinte_parcelles==Vide)faults.Add(t+"l'empreinte des parcelles est celle d'un dessin vide");
            if(v.empreinte_batiments==Vide)faults.Add(t+"l'empreinte des bâtiments est celle d'un dessin vide");
        }

        static void JugerRelance(Rapport r,Rapport jouer,List<string> faults)
        {
            var v=r.ville;var j=jouer.ville;string t="relance, tick "+N(v.tick)+" : ";
            if(j==null||j.tick<0){faults.Add(t+"la session jouer n'a pas de ville relevée à comparer");return;}
            if(v.tick!=j.tick)faults.Add(t+"la ville relancée est au tick "+N(v.tick)+", celle de la session jouer au tick "+N(j.tick));
            if(!v.rues.SequenceEqual(j.rues))faults.Add(t+"rues au plan "+Liste(v.rues)+" pour "+Liste(j.rues)+" dans la session jouer");
            if(!v.rues_posees.SequenceEqual(j.rues_posees))faults.Add(t+"rues posées "+Liste(v.rues_posees)+" pour "+Liste(j.rues_posees)+" dans la session jouer");
            if(!Memes(v.parcelles,j.parcelles))faults.Add(t+"parcelles relancées "+Etats(v.parcelles)+" pour "+Etats(j.parcelles)+" dans la session jouer");
            if(!Memes(v.batiments,j.batiments))faults.Add(t+"bâtiments relancés "+Etats(v.batiments)+" pour "+Etats(j.batiments)+" dans la session jouer");
            if(v.pieces_parcelles!=j.pieces_parcelles||v.pieces_batiments!=j.pieces_batiments)
                faults.Add(t+v.pieces_parcelles+" et "+v.pieces_batiments+" pièce(s) (parcelles, bâtiments) pour "+j.pieces_parcelles+" et "+j.pieces_batiments+" dans la session jouer");
            foreach(var (nom,a,b) in new[]{("rues",v.empreinte_rues,j.empreinte_rues),("parcelles",v.empreinte_parcelles,j.empreinte_parcelles),("bâtiments",v.empreinte_batiments,j.empreinte_batiments)})
                if(a!=b)faults.Add(t+"la ville relancée n'a pas les mêmes "+nom+" : empreinte "+a+" pour "+b);
            if(r.vierge!=jouer.vierge)faults.Add(t+"le sable vierge de cette session n'est pas celui de la session jouer");
        }

        static void JugerVierge(Rapport r,DesertRoadTool tool,Rapport jouer,List<string> faults)
        {
            var v=r.ville;string t="vierge, tick "+N(v.tick)+" : ";
            if(v.rues.Length>0||v.parcelles_plan.Length>0||v.batiments_plan.Length>0)
                faults.Add(t+"le plan d'un service neuf compte "+v.rues.Length+" rue(s) "+Liste(v.rues)+", "+v.parcelles_plan.Length+" parcelle(s) "+Etats(v.parcelles_plan)
                    +" et "+v.batiments_plan.Length+" bâtiment(s) "+Etats(v.batiments_plan));
            if(tool.Parcelles.Count>0||tool.Batiments.Count>0||tool.Ouverture.Count>0)
                faults.Add(t+"contre un service vide, l'outil a dessiné "+tool.Parcelles.Count+" parcelle(s), "+tool.Batiments.Count+" bâtiment(s) et essayé "+tool.Ouverture.Count+" rue(s)");
            if(v.pieces_parcelles!=0||v.pieces_batiments!=0)
                faults.Add(t+v.pieces_parcelles+" pièce(s) sous la racine des parcelles et "+v.pieces_batiments+" sous celle des bâtiments contre un service vide");
            if(v.empreinte_rues!=r.vierge)faults.Add(t+"la ville n'est pas vierge : l'empreinte des rues n'est pas celle du sable vierge");
            if(v.empreinte_parcelles!=Vide)faults.Add(t+"l'empreinte des parcelles "+v.empreinte_parcelles+" n'est pas celle d'un dessin vide ("+Vide+")");
            if(v.empreinte_batiments!=Vide)faults.Add(t+"l'empreinte des bâtiments "+v.empreinte_batiments+" n'est pas celle d'un dessin vide ("+Vide+")");
            if(jouer!=null&&r.vierge!=jouer.vierge)faults.Add(t+"le sable vierge de cette session n'est pas celui de la session jouer");
        }
    }
}
