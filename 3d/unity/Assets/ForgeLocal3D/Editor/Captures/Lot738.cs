using System;using System.Collections;using System.Linq;using Forge.Pont;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 738 : les rues de la base de Biskra en rubans de terre battue, service en pause. 01 de haut, cadré sur les bouts des rubans ;
    // 02 la rue de Lot737 à hauteur d'homme ; 03 une route de geste sur l'axe de cette rue (ou de la suivante), un tick, la même vue.
    static class Lot738
    {
        static DesertRoadTool outil;static DesertCityCamera ville;static int rang=-1;static long seigneurie=-1;static Exception Faux(string m)=>new InvalidOperationException(m);
        // Au moins trois sommets de triangles du ruban devant la caméra, dans la moitié basse de l'image : un ruban sans face n'en a aucun.
        static void Devant(Camera c,int i){var r=DesertRues1400Preuve.Releve(outil.Rues1400.Racine)[i];int n=r.t.Distinct().Select(k=>r.s[k]).Count(v=>{var p=c.WorldToViewportPoint(v);return p.z>c.nearClipPlane&&p.x>0f&&p.x<1f&&p.y>0f&&p.y<.5f;});if(n<3)throw Faux(n+" sommet(s) du ruban "+i+" en bas de l'image");}
        [ScenarioDeCapture(738,"01-biskra-de-haut")]
        static IEnumerator DeHaut(Camera camera)
        {
            outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil");ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw Faux("pas de panneau du lieu");outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            var lus=System.Threading.Tasks.Task.Run(()=>{using(var d=new ClientDeparts(outil.Port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!lus.IsCompleted)yield return null;
            if(lus.IsFaulted||!lus.Result.Presente)throw Faux(lus.IsFaulted?lus.Exception.GetBaseException().Message:lus.Result.Absence);
            var zab=lus.Result.Donnees.Fiches.Where(f=>f.Siege.Nom=="Biskra").ToArray();if(zab.Length!=1)throw Faux(zab.Length+" sièges Biskra");long cellule=zab[0].CellId;seigneurie=zab[0].Id;if(!outil.Ouvrir(cellule))throw Faux(outil.Message);lieu.Ouvrir(cellule);
            var r=outil.Rues1400;var roads=outil.roads;string texte=outil.view.GetComponentsInChildren<TextMesh>().First(t=>t.name=="Panneau des routes").text;
            int iR=texte.IndexOf("Rues de 1400 : 7 dessinée(s) sur 7, 0 coupée(s) au bord du terrain, 0 hors du terrain",StringComparison.Ordinal),iM=texte.IndexOf("Maisons de 1400 : 33 posée(s)",StringComparison.Ordinal);
            if(r.Servies!=7||r.Dessinees!=7||r.Coupees!=0||r.HorsDuTerrain!=0||r.Refus.Count!=0||iR<0||iM<iR||outil.Maisons.Posees!=33)throw Faux("Biskra : "+texte.Replace("\n"," | "));
            // Le terrain ouvert est celui d'une copie vierge, calculée comme DesertCityRelance ; puis la ville est rouverte.
            string emp=roads.Empreintes().Tout,rubans=r.Empreinte;var g=DesertRoads.Lire(roads.implantation);roads.Preparer(g.parametres,g.graine);
            if(roads.Empreintes().Tout!=emp)throw Faux("le sable n'est pas vierge après l'ouverture ("+outil.Ouverture.Count+" rue(s) de geste)");if(!outil.Ouvrir(cellule)||roads.Empreintes().Tout!=emp||r.Empreinte!=rubans)throw Faux("réouverture : "+outil.Message.Replace("\n"," | "));
            r.Dessiner(Lot362.Lire(outil.Port,cellule).Base);var ec=DesertRues1400Preuve.Ecart(DesertRues1400Preuve.Releve(r.Racine),roads.terrain);
            if(roads.Empreintes().Tout!=emp||r.Empreinte!=rubans||r.Racine.childCount!=7||!DesertRues1400Preuve.Dans(ec))throw Faux("second dessin : "+r.Racine.childCount+" rubans, ruban − sol "+ec);
            camera.aspect=1600f/900f;const float incl=68f,cap=40f;var inv=Quaternion.Inverse(Quaternion.Euler(incl,cap,0));float tv=Mathf.Tan(camera.fieldOfView*.5f*Mathf.Deg2Rad),th=tv*camera.aspect,d=40f;
            foreach(var p in DesertRues1400Preuve.Releve(r.Racine).SelectMany(x=>x.s).Concat(outil.Maisons.Racine.Cast<Transform>().Select(e=>e.position+Vector3.up*6f))){var q=inv*p;d=Mathf.Max(d,Mathf.Abs(q.x)/(th*.7f)-q.z,q.y/(tv*.62f)-q.z,-q.y/(tv*.42f)-q.z);}
            ville.Poser(Vector3.zero,cap,incl,d);for(int i=0;i<8;i++)yield return null;outil.Placer();
        }
        [ScenarioDeCapture(738,"02-rue-a-hauteur-d-homme")]
        static IEnumerator Rue(Camera camera)
        {
            if(outil==null)throw Faux("le scénario « 01-biskra-de-haut » n'a pas joué");var plan=Lot362.Lire(outil.Port,outil.Cellule);var (rue,mil)=Lot737.RueBordee(plan);rang=plan.Base.Rues.ToList().IndexOf(rue);
            for(var e=Lot737.AHauteurDHomme(camera,outil,ville,rue,mil);e.MoveNext();)yield return e.Current;Devant(camera,rang);outil.Placer();
        }
        [ScenarioDeCapture(738,"03-apres-le-tick")]
        static IEnumerator ApresLeTick(Camera camera)
        {
            if(rang<0)throw Faux("le scénario « 02-rue-a-hauteur-d-homme » n'a pas joué");var t=outil.roads.terrain;var rues=Lot362.Lire(outil.Port,outil.Cellule).Base.Rues;int choisi=-1;var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
            // Une terre choisie d'abord (#584) ; puis, de haut, deux clics aux bouts de l'axe de la rue de 02, ou de la suivante si l'essai la refuse.
            Lot362.Deposer(outil.Port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+seigneurie+"}");Lot362.Tick(outil.Port);
            for(int k=0;k<2&&choisi<0;k++){int i=(rang+k)%rues.Count;var u=rues[i].Points;var a=Lot362.Monde(t,u[0].X,u[0].Y);var b=Lot362.Monde(t,u[u.Count-1].X,u[u.Count-1].Y);ville.Poser((a+b)/2,ville.Cap,85f,60f);outil.Annuler();
                if(!outil.Clic(camera.WorldToScreenPoint(a))||!outil.Clic(camera.WorldToScreenPoint(b)))throw Faux("clic hors du terrain, rang "+i);var essai=outil.Valider();if(essai!=null&&essai.acceptee)choisi=i;}
            camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);if(choisi<0||outil.Recu==null||!outil.Recu.Acceptee)throw Faux("route de geste refusée : "+outil.Message);
            var avant=DesertRues1400Preuve.Releve(outil.Rues1400.Racine);Lot362.Tick(outil.Port);if(!outil.Attendre())throw Faux("après le tick, aucun plan relu : "+outil.Message);
            float bouge=avant[choisi].s.Max(v=>Mathf.Abs(t.SampleHeight(v)+t.transform.position.y+DesertRues1400.AuDessus-v.y));var apres=DesertRues1400Preuve.Releve(outil.Rues1400.Racine);
            var vieux=DesertRues1400Preuve.Ecart(avant,t);var neuf=DesertRues1400Preuve.Ecart(apres,t);string bilan="rang "+choisi+" : sol bougé de "+bouge.ToString("F3")+" m, anciens "+vieux+", neufs "+neuf+", "+apres.Count+" rubans, "+outil.Maisons.Posees+" maisons";
            if(bouge<=.10f||!DesertRues1400Preuve.Sorti(vieux)||!DesertRues1400Preuve.Dans(neuf)||apres.Count!=7||outil.Maisons.Posees!=33||!outil.Posees.Any(p=>p.resultat.acceptee))throw Faux(bilan+" : "+outil.Message.Replace("\n"," | "));
            Debug.Log("CAPTURE_738 "+bilan);var w=rues[choisi].Points;var mil=new Vector2((float)((w[0].X+w[w.Count-1].X)*.5),(float)((w[0].Y+w[w.Count-1].Y)*.5));
            for(var e=Lot737.AHauteurDHomme(camera,outil,ville,rues[choisi],mil);e.MoveNext();)yield return e.Current;Devant(camera,choisi);outil.Placer();
        }
    }
}
