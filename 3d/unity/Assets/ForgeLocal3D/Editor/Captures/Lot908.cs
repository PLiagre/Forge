using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 908 : à Biskra, le joueur trace son enceinte au clic (E, quatre coins), puis Entrée la dépose au monde ; au tick
    // suivant, le mur aux piquets. -forge908Croise : les coins en sablier, que le monde refuse avec sa raison. -forge908Echap :
    // Échap au lieu d'Entrée, rien ne part. Le second scénario lit l'état du premier dans les champs statiques.
    static class Lot908
    {
        const string Avec="Enceinte : piquets · 4 tour(s), 63 pan(s), 1 porte(s).";
        const string Croisement="enceinte : contour qui se croise";
        static readonly (double x,double y)[] Carre={(-80,-80),(80,-80),(80,80),(-80,80)},Sablier={(-80,-80),(80,80),(80,-80),(-80,80)};
        static DesertRoadTool outil;static DesertCityCamera ville;static long cellule=-1;static string variante;static (double x,double y)[] coins;static string rapport;
        static Exception Faux(string m)=>new InvalidOperationException(m);
        static string Q(string s)=>"\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n")+"\"";
        static string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);
        static string P(double x,double y)=>"["+N(x)+","+N(y)+"]";
        static string Panneau(){var p=outil.view.transform.Find("Panneau des routes")?.GetComponent<TextMesh>();if(!p)throw Faux("la caméra de l'outil n'a pas de panneau");return p.text;}
        static bool Dans(Camera camera,Vector3 v){var q=camera.WorldToViewportPoint(v);return q.z>camera.nearClipPlane&&q.x>.02f&&q.x<.98f&&q.y>.02f&&q.y<.98f;}

        [ScenarioDeCapture(908,"1-trace-en-cours")]
        static IEnumerator TraceEnCours(Camera camera)
        {
            var args=Environment.GetCommandLineArgs();variante=args.Contains("-forge908Croise")?"croise":args.Contains("-forge908Echap")?"echap":"depot";coins=variante=="croise"?Sablier:Carre;
            rapport=Path.Combine(Capture.DossierDesCaptures,"lot908-rapport.json");if(File.Exists(rapport))throw Faux("rapport antérieur : "+rapport);
            outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil");ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw Faux("pas de panneau du lieu");outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            var lus=System.Threading.Tasks.Task.Run(()=>{using(var d=new ClientDeparts(outil.Port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!lus.IsCompleted)yield return null;
            if(lus.IsFaulted||!lus.Result.Presente)throw Faux(lus.IsFaulted?lus.Exception.GetBaseException().Message:lus.Result.Absence);
            var zab=lus.Result.Donnees.Fiches.Where(f=>f.Siege.Nom=="Biskra").ToArray();if(zab.Length!=1)throw Faux(zab.Length+" sièges Biskra");
            long c=zab[0].CellId;string geste="\"maison\":\"seigneurie-"+zab[0].Id+"\",\"cell\":"+c;
            Lot362.Deposer(outil.Port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+zab[0].Id+"}");Lot362.Tick(outil.Port);
            Lot362.Deposer(outil.Port,"{\"type\":\"tracer_route\","+geste+",\"points\":[[-66,2.2],[-120,2.2]],\"largeur_m\":4}");Lot362.Tick(outil.Port);
            if(!outil.Ouvrir(c))throw Faux("ouverture : "+outil.Message);lieu.Ouvrir(c);
            var enc=outil.Enceinte??throw Faux("pas d'enceinte dessinable : "+outil.Message);
            if(outil.Maisons.Posees!=33||outil.Rues1400.Dessinees!=7||enc.Posees!=0)throw Faux(outil.Maisons.Posees+" maisons, "+outil.Rues1400.Dessinees+" rues de 1400, "+enc.Posees+" pièces d'enceinte");
            // Les clics, de haut, sur une image de la taille de la photo : chaque coin au milieu de l'écran.
            var t=outil.roads.terrain;outil.EntrerEnceinte();var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
            try{foreach(var (x,y) in coins){var m=Lot362.Monde(t,x,y);ville.Poser(m,ville.Cap,85f,60f);if(!outil.Clic(camera.WorldToScreenPoint(m)))throw Faux("clic en "+P(x,y)+" refusé : "+outil.Message);}}
            finally{camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);}
            if(!Panneau().Split('\n').Contains("Enceinte · 4 coin(s)"))throw Faux("panneau : "+Panneau());
            var trait=outil.TraceEnceinte??throw Faux("pas de tracé : "+Panneau());
            if(!trait.enabled||!trait.loop)throw Faux("tracé "+(trait.enabled?"activé":"désactivé")+", loop "+trait.loop);
            var sommets=new Vector3[trait.positionCount];trait.GetPositions(sommets);
            foreach(var (x,y) in coins)if(!sommets.Any(v=>new Vector2(v.x+(float)x,v.z+(float)y).magnitude<.05f))throw Faux("aucun sommet au coin "+P(x,y)+" ("+sommets.Length+" sommets)");
            foreach(var v in sommets)if(Mathf.Abs(v.y-(t.SampleHeight(v)+t.transform.position.y)-1f)>.01f)throw Faux("sommet "+v+" hors de 1 m au-dessus du sol");
            if(Lot362.Lire(outil.Port,c).Enceinte!=null)throw Faux("enceinte au plan sans Entrée");
            cellule=c;
            // Surplomb à 65° : la caméra recule jusqu'à tenir les quatre coins entre 0,02 et 0,98 de l'image.
            camera.aspect=1600f/900f;var cibles=coins.Select(p=>Lot362.Monde(t,p.x,p.y)).ToArray();bool cadre=false;
            for(float d=60f;d<=DesertCityCamera.DistanceMax&&!cadre;d*=1.06f){ville.Poser(Lot362.Monde(t,0,0),ville.Cap,65f,d);cadre=cibles.All(v=>Dans(camera,v));}
            if(!cadre)throw Faux("les quatre coins ne tiennent pas dans l'image");
            outil.Placer();for(int i=0;i<10;i++)yield return null;
        }

        [ScenarioDeCapture(908,"2-enceinte-en-chantier")]
        static IEnumerator EnceinteEnChantier(Camera camera)
        {
            if(outil==null||ville==null||cellule<0)throw Faux("le scénario « 1-trace-en-cours » n'a pas joué");
            bool depot=variante=="depot",croise=variante=="croise",echap=variante=="echap";var enc=outil.Enceinte;var t=outil.roads.terrain;
            RecuIntention recu=null;if(echap)outil.Annuler();else recu=outil.ValiderEnceinte();
            if(!echap&&(outil.Derniers.Length!=4||!outil.Derniers.SequenceEqual(coins)))throw Faux("coins déposés "+string.Join(" ",outil.Derniers.Select(p=>P(p.x,p.y))));
            string[] lignes=Panneau().Split('\n');
            if(depot)
            {
                if(recu==null||recu!=outil.Recu||!recu.Acceptee)throw Faux("dépôt non accepté : "+Panneau());
                string attendu="Enceinte déposée au monde : elle se dessine au tick suivant (après le tick "+recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture)+").";
                if(lignes[0]!=attendu)throw Faux("panneau : "+Panneau());
            }
            else if(croise)
            {
                if(recu==null||!recu.Presente||recu.Acceptee||recu.Erreur!=Croisement)throw Faux("reçu : "+(recu==null?"null":recu.Erreur??recu.Absence));
                if(lignes[0]!="Le monde refuse l'enceinte : "+Croisement)throw Faux("panneau : "+Panneau());
            }
            else
            {
                if(outil.ModeEnceinte||outil.Recu!=null)throw Faux("après Échap : mode enceinte "+outil.ModeEnceinte+", reçu "+(outil.Recu!=null));
                if(lignes.Any(l=>l.Contains("point(s)")||l.Contains("coin(s)")))throw Faux("Échap garde des coins : "+Panneau());
            }
            var trait=outil.TraceEnceinte;if(trait&&(trait.enabled||trait.positionCount!=0))throw Faux("tracé encore activé : "+trait.positionCount+" sommets");
            if(outil.Attendre())throw Faux("Attendre vrai avant le tick");
            Lot362.Tick(outil.Port);bool dessine=outil.Attendre();
            if(dessine!=depot)throw Faux("Attendre "+dessine+" après le tick, variante "+variante);
            var plan=Lot362.Lire(outil.Port,cellule);var e=plan.Enceinte;
            if(depot)
            {
                bool contour=e!=null&&e.Contour.Count==4&&e.Contour.Select(p=>(p.X,p.Y)).SequenceEqual(coins);
                if(!contour||!e.EnChantier||e.TravailRequis!=19200||PansDeLEnceinte.Etape(e)!=EtapeDuBatiment.Piquets||!plan.Portes.Any(p=>p.Point.X==-80&&p.Point.Y==2.2))
                    throw Faux("plan du tick "+plan.Tick+" : "+(e==null?"enceinte absente":"contour "+contour+", chantier "+e.EnChantier+", "+e.TravailFourni+"/"+e.TravailRequis)+", "+plan.Portes.Count+" porte(s)");
                if(enc.Posees!=68||enc.Racine.childCount!=68)throw Faux(enc.Posees+" posées, "+enc.Racine.childCount+" enfants");
                var porte=enc.Racine.Find("Enceinte porte 3-0");if(!porte||Quaternion.Angle(porte.rotation,Quaternion.Euler(0,90,0))>=.01f)throw Faux("Enceinte porte 3-0 "+(porte?"au lacet "+porte.eulerAngles.y:"absente"));
                if(!Panneau().Split('\n').Contains(Avec))throw Faux("panneau : "+Panneau());
            }
            else
            {
                if(e!=null||plan.Portes.Count>0)throw Faux("plan du tick "+plan.Tick+" : enceinte "+(e!=null)+", "+plan.Portes.Count+" porte(s)");
                if(enc.Posees!=0)throw Faux(enc.Posees+" pièces posées");
                if(Panneau().Split('\n').Any(l=>l.StartsWith("Enceinte :",StringComparison.Ordinal)))throw Faux("ligne d'enceinte sans mur : "+Panneau());
            }
            // De l'ouest à 35°, dos à la porte : les tours (−80 ; ±80) et la porte tiennent dans l'image.
            float lacet=depot?(float)PansDeLEnceinte.Decouper(e,plan.Portes).Pieces.Last(p=>p.Nature==NatureDePiece.Porte).LacetDegres:90f;
            camera.aspect=1600f/900f;var cibles=new[]{Lot362.Monde(t,-80,-80),Lot362.Monde(t,-80,80),Lot362.Monde(t,-80,2.2)};bool cadre=false;
            for(float d=40f;d<=DesertCityCamera.DistanceMax&&!cadre;d*=1.06f){ville.Poser(Lot362.Monde(t,-80,0),lacet+180f,35f,d);cadre=cibles.All(v=>Dans(camera,v))&&camera.transform.position.x>80f;}
            if(!cadre)throw Faux("cadrage impossible, caméra "+camera.transform.position);
            outil.Placer();for(int i=0;i<10;i++)yield return null;
            var r=outil.Recu;
            string bilan="{\"cellule\":"+cellule+",\"tick\":"+plan.Tick+",\"variante\":"+Q(variante)+",\"coins\":["+string.Join(",",coins.Select(p=>P(p.x,p.y)))+"]"
                +",\"recu\":"+(r==null?"null":"{\"acceptee\":"+(r.Acceptee?"true":"false")+",\"tick\":"+(r.AppliqueeAuTick?.ToString(CultureInfo.InvariantCulture)??"null")+",\"erreur\":"+(r.Erreur==null?"null":Q(r.Erreur))+"}")
                +",\"enceinte\":"+(e==null?"null":"{\"contour\":["+string.Join(",",e.Contour.Select(p=>P(p.X,p.Y)))+"],\"en_chantier\":"+(e.EnChantier?"true":"false")+",\"travail_fourni\":"+e.TravailFourni+",\"travail_requis\":"+e.TravailRequis+"}")
                +",\"portes\":["+string.Join(",",plan.Portes.Select(p=>"{\"point\":"+P(p.Point.X,p.Point.Y)+",\"rue\":"+Q(p.Rue)+",\"identifiant\":"+p.Identifiant+"}"))+"]"
                +",\"posees\":"+enc.Posees+",\"empreinte\":"+Q(enc.Empreinte)+",\"panneau\":"+Q(Panneau())+"}";
            File.WriteAllText(rapport,bilan);Debug.Log("CAPTURE_908 "+bilan);
        }
    }
}
