using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using Forge.Pont;
using UnityEditor;
using UnityEngine;
using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 907 : Biskra vue de l'ouest, l'enceinte aux piquets. Rejoue le lot 904, puis exige les pièces du kit.
    // -forge907SansEnceinte : aucune pièce. -forge907SansPorte : la porte aux piquets manque, et le pan qu'elle ôte.
    static class Lot907
    {
        const string Avec="Enceinte : piquets · 4 tour(s), 63 pan(s), 1 porte(s).";
        const string SansPorteLigne="Enceinte : piquets · 4 tour(s), 63 pan(s), 0 porte(s).";
        const string RefusPorte="Pièce 67 de l'enceinte non posée : pièce manquante au kit : porte piquets";
        static Exception Faux(string m)=>new InvalidOperationException(m);
        static string Q(string s)=>"\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n")+"\"";
        static string N(float v)=>v.ToString("R",CultureInfo.InvariantCulture);
        static string Nom(NatureDePiece n)=>n==NatureDePiece.Tour?"tour":n==NatureDePiece.Porte?"porte":"courtine";
        static string Prefab(Transform tr)
        {
            string vu="";foreach(Transform c in tr){int k=c.name.LastIndexOf("_LOD",StringComparison.Ordinal);if(k>0){vu=c.name.Substring(0,k);break;}}
            var src=PrefabUtility.GetCorrespondingObjectFromSource(tr.gameObject);
            if(src&&vu.Length>0&&src.name!=vu)throw Faux(tr.name+" : prefab "+src.name+" contre "+vu);
            return src?src.name:vu;
        }
        [ScenarioDeCapture(907,"biskra-enceinte")]
        static IEnumerator BiskraEnceinte(Camera camera)
        {
            var args=Environment.GetCommandLineArgs();bool sans=args.Contains("-forge907SansEnceinte"),sansPorte=args.Contains("-forge907SansPorte");
            string rapport=Path.Combine(Capture.DossierDesCaptures,"lot907-rapport.json");if(File.Exists(rapport))throw Faux("rapport antérieur : "+rapport);
            var outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil");var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw Faux("pas de panneau du lieu");outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            var lus=System.Threading.Tasks.Task.Run(()=>{using(var d=new ClientDeparts(outil.Port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!lus.IsCompleted)yield return null;
            if(lus.IsFaulted||!lus.Result.Presente)throw Faux(lus.IsFaulted?lus.Exception.GetBaseException().Message:lus.Result.Absence);
            var zab=lus.Result.Donnees.Fiches.Where(f=>f.Siege.Nom=="Biskra").ToArray();if(zab.Length!=1)throw Faux(zab.Length+" sièges Biskra");
            long cellule=zab[0].CellId;string geste="\"maison\":\"seigneurie-"+zab[0].Id+"\",\"cell\":"+cellule;
            Lot362.Deposer(outil.Port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+zab[0].Id+"}");Lot362.Tick(outil.Port);
            Lot362.Deposer(outil.Port,"{\"type\":\"tracer_route\","+geste+",\"points\":[[-66,2.2],[-120,2.2]],\"largeur_m\":4}");
            if(!sans)Lot362.Deposer(outil.Port,"{\"type\":\"tracer_enceinte\","+geste+",\"points\":[[-80,-80],[80,-80],[80,80],[-80,80]],\"foyers\":2}");
            Lot362.Tick(outil.Port);Lot362.Tick(outil.Port);
            var plan=Lot362.Lire(outil.Port,cellule);var e=plan.Enceinte;
            // Graine 0, 30 jours déjà joués : les deux ticks paient 20 journées, le requis reste 19200, donc les piquets.
            bool mur=e!=null&&e.EnChantier&&e.TravailFourni==20&&e.TravailRequis==19200,portePlan=plan.Portes.Any(p=>p.Point.X==-80&&p.Point.Y==2.2);
            if(sans?e!=null||plan.Portes.Count>0:!(mur&&portePlan))throw Faux("plan du tick "+plan.Tick+" : "+(e==null?"enceinte absente":"fourni "+e.TravailFourni+"/"+e.TravailRequis+" chantier "+e.EnChantier)+", porte "+portePlan);
            var enc=outil.Enceinte??throw Faux("pas d'enceinte dessinée");
            if(sansPorte){var kit=Object.Instantiate(enc.Kit);foreach(var n in kit.natures)if(n!=null&&n.nature=="porte")n.piquets=null;enc.Kit=kit;}
            if(!outil.Ouvrir(cellule))throw Faux("ouverture : "+outil.Message);lieu.Ouvrir(cellule);
            if(outil.Maisons.Posees!=33||outil.Rues1400.Dessinees!=7)throw Faux(outil.Maisons.Posees+" maisons, "+outil.Rues1400.Dessinees+" rues de 1400");
            int attendus=sans?0:sansPorte?67:68;
            if(enc.Posees!=attendus||enc.Racine.childCount!=enc.Posees)throw Faux(enc.Posees+" posées, "+enc.Racine.childCount+" enfants ; attendu "+attendus);
            bool Ligne(string s)=>outil.Message.Split('\n').Contains(s);
            if(sans){if(outil.Message.Split('\n').Any(l=>l.StartsWith("Enceinte")))throw Faux("ligne d'enceinte sans mur");if(enc.Refus.Count!=0)throw Faux(string.Join(" | ",enc.Refus));}
            else if(sansPorte){var msg=outil.Message.Split('\n');int k=Array.IndexOf(msg,SansPorteLigne);if(k<0||k+1>=msg.Length||msg[k+1]!=RefusPorte)throw Faux("panneau : "+outil.Message);if(enc.Refus.Count!=1||enc.Refus[0]!=RefusPorte)throw Faux(string.Join(" | ",enc.Refus));}
            else if(!Ligne(Avec)||enc.Refus.Count!=0)throw Faux("panneau : "+outil.Message);
            if(enc.Racine.Find("Enceinte courtine 3-7"))throw Faux("le pan 7 du côté ouest est posé");
            var porteGo=enc.Racine.Find("Enceinte porte 3-0");
            if(sansPorte&&porteGo)throw Faux("la porte est posée");if(!sans&&!sansPorte&&!porteGo)throw Faux("porte 3-0 absente");
            if(porteGo&&Quaternion.Angle(porteGo.rotation,Quaternion.Euler(0,90,0))>=.01f)throw Faux("Enceinte porte 3-0 : lacet "+porteGo.eulerAngles.y.ToString(CultureInfo.InvariantCulture));
            if(!sans)
            {
                var d=PansDeLEnceinte.Decouper(e,plan.Portes);if(!d.Presente)throw Faux("découpe : "+d.Absence);var solT=outil.roads.terrain;int tours=0,pans=0,nb=0;
                foreach(var p in d.Pieces)
                {
                    string nom=Nom(p.Nature),attendu=p.Nature==NatureDePiece.Tour?"chantier_tour_ksar_0_piquets":p.Nature==NatureDePiece.Porte?"chantier_porte_ksar_piquets":"chantier_rempart_pise_10m_piquets";
                    var tr=enc.Racine.Find("Enceinte "+nom+" "+p.Cote+"-"+p.Indice);
                    if(!tr){if(!(sansPorte&&p.Nature==NatureDePiece.Porte))throw Faux("pièce absente : "+nom+" "+p.Cote+"-"+p.Indice);continue;}
                    var sol=Lot362.Monde(solT,p.CentreX,p.CentreY);
                    if(new Vector2(tr.position.x-sol.x,tr.position.z-sol.z).magnitude>=.01f)throw Faux(tr.name+" : écart horizontal");
                    if(Quaternion.Angle(tr.rotation,Quaternion.Euler(0,(float)p.LacetDegres,0))>=.01f)throw Faux(tr.name+" : lacet");
                    if(Mathf.Abs(tr.position.y-sol.y)>=.01f)throw Faux(tr.name+" : pied hors du sol");
                    string prefab=Prefab(tr);if(prefab!=attendu)throw Faux(tr.name+" : prefab "+(prefab.Length==0?"absent":prefab));
                    if(p.Nature==NatureDePiece.Tour)tours++;else if(p.Nature==NatureDePiece.Porte)nb++;else pans++;
                }
                if(tours!=4||pans!=63||nb!=(sansPorte?0:1))throw Faux(tours+" tours, "+pans+" pans, "+nb+" portes");
            }
            int enfants=enc.Racine.childCount;string empreinte=enc.Empreinte;if(!outil.Rafraichir())throw Faux("rafraîchir : "+outil.Message);
            if(enc.Empreinte!=empreinte||enc.Racine.childCount!=enfants||enc.Posees!=attendus)throw Faux("après rafraîchir "+enc.Racine.childCount+" enfants, "+enc.Posees+" posées");
            if(sans?outil.Message.Split('\n').Any(l=>l.StartsWith("Enceinte")):!Ligne(sansPorte?SansPorteLigne:Avec))throw Faux("panneau après rafraîchir : "+outil.Message);
            float lacet=sans?90f:(float)PansDeLEnceinte.Decouper(e,plan.Portes).Pieces.Last(p=>p.Nature==NatureDePiece.Porte).LacetDegres;
            var t=outil.roads.terrain;camera.aspect=1600f/900f;var cibles=new[]{Lot362.Monde(t,-80,-80),Lot362.Monde(t,-80,80),Lot362.Monde(t,-80,2.2)};
            bool Dans(Vector3 v){var q=camera.WorldToViewportPoint(v);return q.z>camera.nearClipPlane&&q.x>.02f&&q.x<.98f&&q.y>.02f&&q.y<.98f;}
            bool cadre=false;for(float dist=40f;dist<=DesertCityCamera.DistanceMax&&!cadre;dist*=1.06f){ville.Poser(Lot362.Monde(t,-80,0),lacet+180f,35f,dist);cadre=cibles.All(Dans)&&camera.transform.position.x>80f;}
            if(!cadre)throw Faux("cadrage impossible, caméra "+camera.transform.position.ToString());
            outil.Placer();for(int i=0;i<10;i++)yield return null;
            var pieces=enc.Racine.Cast<Transform>().Select(tr=>"{\"nom\":"+Q(tr.name)+",\"prefab\":"+Q(Prefab(tr))+",\"position\":["+N(tr.position.x)+","+N(tr.position.y)+","+N(tr.position.z)+"],\"lacet\":"+N(tr.eulerAngles.y)+"}");
            string etape=e==null?"null":Q(PansDeLEnceinte.Etape(e).ToString().ToLowerInvariant());
            string bilan="{\"cellule\":"+cellule+",\"tick\":"+plan.Tick+",\"etape\":"+etape+",\"travail_fourni\":"+(e==null?"null":e.TravailFourni.ToString(CultureInfo.InvariantCulture))+",\"travail_requis\":"+(e==null?"null":e.TravailRequis.ToString(CultureInfo.InvariantCulture))
                +",\"pieces\":["+string.Join(",",pieces)+"],\"posees\":"+enc.Posees+",\"refus\":["+string.Join(",",enc.Refus.Select(Q))+"],\"empreinte\":"+Q(enc.Empreinte)+",\"panneau\":"+Q(outil.Message)+"}";
            File.WriteAllText(rapport,bilan);Debug.Log("CAPTURE_907 "+bilan);
        }
    }
}
