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
    // Contrôle du lot 370, en Play : les bâtiments de la capitale vivent dans le monde, pas dans Unity.
    // Trois sessions, chacune un lancement d'Unity sur la première implantation de la sélection, sur la
    // mécanique de DesertCityRelance (recopiée, clés de session à elle) : `Poser` (service neuf) pose une
    // maison, une scierie et un four et relève la ville rouverte à chacun des trois ticks qui suivent ;
    // `Relancer` (même service) rouvre la ville et doit retrouver les mêmes pièces aux mêmes places ;
    // `Vierge` (service neuf) n'en doit poser aucune. L'étape attendue se calcule ici, d'après les nombres
    // du plan, sans passer par la vue. Rien n'est capturé.
    [InitializeOnLoad] public static class DesertCityBatiments
    {
        const string Flag="Forge.Desert.Batiments",Cle="Forge.Desert.Batiments.Session",Id="Forge.Desert.Batiments.Implantation";
        const string Output=DesertRoads.Sorties;
        static int last=-1,settle;
        // La recette : trois parcelles de 10 m × 15 m à gauche de la rue de plaine, puis une pièce de chaque nature.
        static readonly int[] SEGMENTS={4,6,8};
        static readonly (string nature,int foyers)[] POSES={("maison",24),("scierie",12),("four",1)};
        static readonly string[] SEQUENCE={"piquets","murs","fini"};
        static readonly string Vide=Hacher("");

        [Serializable] class Selection{public string[] implantations;}
        [Serializable] public class Batiment{public long identifiant=-1;public string nature="";public long fourni=-1,requis=-1;public bool en_chantier;public string attendue="",dessinee="",message="";public bool maillages;}
        [Serializable] public class Releve{public long tick=-1;public Batiment[] batiments=new Batiment[0];public int pieces=-1;public string empreinte="";}
        [Serializable] public class Rapport
        {
            public string session="",implantation="";public long cell=-1;public int port=-1;public long tick_ouverture=-1;
            public Releve ouverture=new Releve();public Releve[] ticks=new Releve[0];public string[] sequence_maison=new string[0];public string[] defauts=new string[0];
        }

        static DesertCityBatiments(){EditorApplication.update+=Tick;}

        public static void Poser()=>Lancer("poser");
        public static void Relancer()=>Lancer("relance");
        public static void Vierge()=>Lancer("vierge");

        static void Lancer(string session)
        {
            var selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
            if(selection?.implantations==null||selection.implantations.Length==0)
                throw new InvalidOperationException("Aucune implantation : lancer py local3d/atelier_desert.py batiments");
            string id=selection.implantations[0];
            SessionState.SetString(Cle,session);SessionState.SetString(Id,id);
            EditorSceneManager.OpenScene(ScenePath(id));
            SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static string ScenePath(string id)=>DesertBuilder.Root+"/Scenes/Forge_Desert_Ville_"+id+".unity";
        static string Chemin(string id,string session)=>Output+id+"/batiments/"+session+".json";

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
            // Une exception (une aide de Lot362, par exemple) est un défaut : le rapport est écrit quand même.
            catch(Exception e){Debug.LogException(e);faults.Add("exception : "+e.GetBaseException().Message);}
            report.defauts=faults.ToArray();
            try
            {
                Directory.CreateDirectory(Output+id+"/batiments");
                File.WriteAllText(Chemin(id,session),JsonUtility.ToJson(report,true));
                Debug.Log("DESERT_BATIMENTS "+session+" "+id+" "+string.Join(" | ",report.defauts));
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
        static EtapeDuBatiment Etape(string etat)=>etat=="piquets"?EtapeDuBatiment.Piquets:etat=="murs"?EtapeDuBatiment.Murs:EtapeDuBatiment.Fini;
        // Les maillages d'une pièce, dans l'ordre de sa hiérarchie, tous LOD compris (comme Lot369.Maillages).
        static Mesh[] Maillages(GameObject go)=>go.GetComponentsInChildren<MeshFilter>(true).Select(f=>f.sharedMesh).Where(m=>m!=null).ToArray();

        static void Run(Rapport report,List<string> faults)
        {
            var tool=Object.FindFirstObjectByType<DesertRoadTool>();
            if(!tool)throw new InvalidOperationException("Scène sans outil des routes : relancer py local3d/atelier_desert.py terrain");
            tool.automatique=true;
            report.cell=tool.Cellule;report.port=tool.Port;report.tick_ouverture=tool.TickOuverture;
            var kit=KitDesBatiments.Charger();
            if(!kit)faults.Add("pas de kit des bâtiments (Resources/"+KitDesBatiments.Ressource+") : aucune pièce ne se compare");
            report.ouverture=Relever(tool,kit,tool.TickOuverture,faults);
            if(report.tick_ouverture<0)faults.Add("l'outil n'a pas lu de plan à l'ouverture (tick_ouverture -1) : "+tool.Message);
            if(report.session=="poser"){if(Recette(tool,kit,report,faults))JugerPoser(report,faults);}
            else if(report.session=="relance")
            {
                string chemin=Chemin(report.implantation,"poser");
                if(!File.Exists(chemin))faults.Add("rapport de la session poser absent : "+chemin);
                else JugerRelance(report,JsonUtility.FromJson<Rapport>(File.ReadAllText(chemin)),faults);
            }
            else JugerVierge(report,tool,faults);
        }

        // La ville telle que l'outil vient de la dessiner, bâtiment du plan par bâtiment du plan.
        static Releve Relever(DesertRoadTool tool,KitDesBatiments kit,long dessine,List<string> faults)
        {
            var plan=Lot362.Lire(tool.Port,tool.Cellule);var racine=tool.RacineBatiments;
            if(plan.Tick!=dessine)faults.Add("relevé : le plan relu est au tick "+N(plan.Tick)+", l'outil a dessiné celui du tick "+N(dessine));
            var r=new Releve{tick=plan.Tick,pieces=racine?racine.childCount:-1,empreinte=tool.EmpreinteBatiments};
            r.batiments=plan.Batiments.Select(b=>
            {
                // Calculée ici d'après les nombres du plan : une étape mal lue par la vue doit se voir.
                string attendue=!b.EnChantier?"fini":2*b.TravailFourni<b.TravailRequis?"piquets":"murs";
                int i=tool.Batiments.FindIndex(e=>e.identifiant==b.Identifiant);
                var piece=racine!=null?racine.Find("Bâtiment "+N(b.Identifiant)):null;var prefab=kit!=null?kit.Piece(b.Nature,Etape(attendue)):null;
                bool maillages=piece!=null&&prefab!=null&&prefab.Presente&&Maillages(prefab.Prefab).Length>0&&Maillages(piece.gameObject).SequenceEqual(Maillages(prefab.Prefab));
                return new Batiment{identifiant=b.Identifiant,nature=b.Nature,fourni=b.TravailFourni,requis=b.TravailRequis,en_chantier=b.EnChantier,
                    attendue=attendue,dessinee=i<0?"absente":tool.Batiments[i].etat,message=i<0?"":tool.Batiments[i].message??"",maillages=maillages};
            }).ToArray();
            return r;
        }

        // Service neuf : la rue de plaine, trois parcelles achevées, trois poses, puis trois ticks, la ville rouverte à chacun.
        // Rend faux si la session s'est arrêtée avant les poses.
        static bool Recette(DesertRoadTool tool,KitDesBatiments kit,Rapport report,List<string> faults)
        {
            int port=tool.Port;long cell=tool.Cellule;
            var g=DesertRoads.Lire(report.implantation).routes.FirstOrDefault(x=>x.famille=="plaine");
            if(g==null){faults.Add("jeu de gestes sans route plaine");return false;}
            Lot362.Deposer(port,tool.Intention(g));Lot362.Tick(port);
            var plan=Lot362.Lire(port,cell);long rue=Lot362.Identifiant(plan,g);int n0=plan.Parcelles.Count;
            string decoupe="{\"type\":\"decouper_parcelle\",\"cell\":"+N(cell)+",\"rue\":"+N(rue)+",\"segment\":";
            const string MESURES=",\"debut_m\":0,\"facade_m\":10,\"profondeur_m\":15,\"cote\":\"gauche\",\"foyers\":100}";
            Lot362.Deposer(port,SEGMENTS.Select(s=>decoupe+N(s)+MESURES).ToArray());
            Lot362.Tick(port);Lot362.Tick(port);
            plan=Lot362.Lire(port,cell);var parcelles=plan.Parcelles.Skip(n0).Take(SEGMENTS.Length).ToArray();
            if(parcelles.Length!=SEGMENTS.Length||parcelles.Any(p=>p.EnChantier))
            {
                faults.Add("les trois parcelles découpées ne sont pas achevées au plan du tick "+N(plan.Tick)+" : ["
                    +string.Join(", ",parcelles.Select(p=>N(p.Identifiant)+" "+N(p.TravailFourni)+"/"+N(p.TravailRequis)))+"]");
                return false;
            }
            Lot362.Deposer(port,Enumerable.Range(0,POSES.Length).Select(i=>"{\"type\":\"poser_batiment\",\"cell\":"+N(cell)+",\"parcelle\":"+N(parcelles[i].Identifiant)
                +",\"nature\":\""+POSES[i].nature+"\",\"foyers\":"+N(POSES[i].foyers)+"}").ToArray());
            var ticks=new List<Releve>();
            for(int k=0;k<3;k++)
            {
                Lot362.Tick(port);
                if(!tool.Ouvrir())faults.Add("après le tick "+(k+1)+" des poses, l'outil n'a pas rouvert la ville : "+tool.Message);
                ticks.Add(Relever(tool,kit,tool.TickOuverture,faults));
            }
            report.ticks=ticks.ToArray();
            // L'étape dessinée de la maison à chaque relevé, les répétitions qui se suivent fusionnées.
            var sequence=new List<string>();
            foreach(var r in report.ticks)
            {
                string e=r.batiments.FirstOrDefault(b=>b.nature=="maison")?.dessinee??"absente";
                if(sequence.Count==0||sequence[sequence.Count-1]!=e)sequence.Add(e);
            }
            report.sequence_maison=sequence.ToArray();
            return true;
        }

        static string Nomme(Batiment b,long tick)=>"bâtiment "+N(b.identifiant)+" ("+b.nature+", "+N(b.fourni)+"/"+N(b.requis)+") au tick "+N(tick);
        static string Liste(Releve r)=>"["+string.Join(", ",r.batiments.Select(b=>N(b.identifiant)+" "+b.nature+" "+b.dessinee))+"]";
        static int Posees(Releve r)=>r.batiments.Count(b=>b.dessinee!="refusee"&&b.dessinee!="absente");

        // Chaque bâtiment est dessiné à l'étape que disent ses nombres, avec la pièce du kit de cette étape.
        static void JugerPieces(Releve r,List<string> faults)
        {
            foreach(var b in r.batiments)
            {
                if(b.dessinee!=b.attendue)faults.Add(Nomme(b,r.tick)+" : dessiné "+b.dessinee+" au lieu de "+b.attendue+(b.message.Length>0?" ("+b.message+")":""));
                if(!b.maillages)faults.Add(Nomme(b,r.tick)+" : la pièce sous la racine n'a pas les maillages de "+b.nature+" "+b.attendue+" au kit");
            }
        }

        static void JugerPoser(Rapport r,List<string> faults)
        {
            if(r.ouverture.batiments.Length>0||r.ouverture.pieces!=0)
                faults.Add("le service n'est pas neuf : "+r.ouverture.batiments.Length+" bâtiment(s) au plan et "+r.ouverture.pieces+" pièce(s) à l'ouverture");
            if(r.ticks.Length!=3)faults.Add(r.ticks.Length+" relevé(s) après les poses au lieu de 3");
            foreach(var t in r.ticks)
            {
                if(t.batiments.Length!=3)faults.Add("tick "+N(t.tick)+" : "+t.batiments.Length+" bâtiment(s) au plan au lieu de 3 "+Liste(t));
                JugerPieces(t,faults);
                if(t.pieces!=Posees(t)||t.pieces!=3)faults.Add("tick "+N(t.tick)+" : "+t.pieces+" pièce(s) sous la racine des bâtiments pour "+Posees(t)+" posée(s), il en faut 3");
            }
            if(!r.sequence_maison.SequenceEqual(SEQUENCE))
                faults.Add("la maison passe par "+string.Join(", ",r.sequence_maison)+" au lieu de "+string.Join(", ",SEQUENCE));
            if(r.ticks.Length==0)return;
            var fin=r.ticks[r.ticks.Length-1];
            foreach(var (nature,etat) in new[]{("maison","fini"),("scierie","murs"),("four","piquets")})
            {
                var b=fin.batiments.FirstOrDefault(x=>x.nature==nature);
                if(b==null)faults.Add("tick "+N(fin.tick)+" : pas de "+nature+" au plan, les trois étapes ne sont pas là ensemble");
                else if(b.dessinee!=etat)faults.Add(Nomme(b,fin.tick)+" : dessiné "+b.dessinee+" au lieu de "+etat+", les trois étapes ne sont pas là ensemble");
            }
            if(fin.empreinte==Vide)faults.Add("tick "+N(fin.tick)+" : l'empreinte des bâtiments est celle d'un plan sans bâtiment");
        }

        static void JugerRelance(Rapport r,Rapport poser,List<string> faults)
        {
            if(poser.ticks==null||poser.ticks.Length==0){faults.Add("la session poser n'a aucun relevé à comparer");return;}
            var fin=poser.ticks[poser.ticks.Length-1];var o=r.ouverture;
            if(o.tick!=fin.tick)faults.Add("la ville relancée est au tick "+N(o.tick)+", la session poser s'est arrêtée au tick "+N(fin.tick));
            if(!o.batiments.Select(b=>(b.identifiant,b.nature,b.dessinee)).SequenceEqual(fin.batiments.Select(b=>(b.identifiant,b.nature,b.dessinee))))
                faults.Add("bâtiments relancés "+Liste(o)+" différents de ceux du tick "+N(fin.tick)+" de la session poser "+Liste(fin));
            JugerPieces(o,faults);
            if(o.pieces!=fin.pieces)faults.Add(o.pieces+" pièce(s) sous la racine des bâtiments relancés pour "+fin.pieces+" au tick "+N(fin.tick)+" de la session poser");
            if(o.empreinte!=fin.empreinte)faults.Add("la ville relancée ne repose pas les mêmes pièces aux mêmes places : empreinte "+o.empreinte+" pour "+fin.empreinte);
        }

        static void JugerVierge(Rapport r,DesertRoadTool tool,List<string> faults)
        {
            var o=r.ouverture;
            if(o.batiments.Length>0)faults.Add("le plan d'un service neuf compte "+o.batiments.Length+" bâtiment(s) "+Liste(o));
            if(tool.Batiments.Count>0)faults.Add(tool.Batiments.Count+" bâtiment(s) dessiné(s) contre un service vide : "+string.Join(", ",tool.Batiments.Select(e=>N(e.identifiant)+" "+e.etat)));
            if(o.pieces!=0)faults.Add(o.pieces+" pièce(s) sous la racine des bâtiments contre un service vide");
            if(o.empreinte!=Vide)faults.Add("l'empreinte des bâtiments "+o.empreinte+" n'est pas celle d'un plan sans bâtiment ("+Vide+")");
        }
    }
}
