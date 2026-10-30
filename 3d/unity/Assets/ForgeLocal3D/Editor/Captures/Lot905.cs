using System;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.IO;using System.Linq;using UnityEditor;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 905 : la galerie des étapes de chantier de l'enceinte, posée au bord de la ville de 1400. Trois rangées lues dans selection.json
    // (courtine, tour, porte), trois colonnes (piquets, levée à mi-hauteur, pièce finie), LOD0 forcé, les façades tournées vers la caméra.
    // Sous -forge905FinisSeuls, la colonne du fini seule : trois pièces.
    static class Lot905
    {
        [Serializable] class Rangee{public string fini;public string[] etapes;}
        [Serializable] class Selection{public Rangee[] planche;}
        static readonly string[] Finis={"rempart_pise_10m","tour_ksar_0","porte_ksar"};
        static Exception Faux(string m)=>new InvalidOperationException(m);static string N(float v)=>v.ToString("R",CultureInfo.InvariantCulture);static string V(Vector3 v)=>"["+N(v.x)+","+N(v.y)+","+N(v.z)+"]";
        static Renderer[] Lod0(GameObject o){var g=o.GetComponent<LODGroup>();return g&&g.lodCount>0?g.GetLODs()[0].renderers.Where(r=>r).ToArray():o.GetComponentsInChildren<Renderer>(true);}
        static int Actifs(GameObject o)=>Lod0(o).Count(r=>r.enabled&&r.gameObject.activeInHierarchy);
        [ScenarioDeCapture(905,"galerie-enceinte")]
        static IEnumerator GalerieEnceinte(Camera camera)
        {
            string rapport=Path.Combine(Capture.DossierDesCaptures,"lot905-rapport.json");if(File.Exists(rapport))throw Faux("rapport antérieur : "+rapport);
            bool seuls=Environment.GetCommandLineArgs().Contains("-forge905FinisSeuls");
            // Les rangées de la planche du kit (lot 270), écrites par Python d'après kit.CHANTIERS : jamais recopiées ici.
            string chemin=Path.GetFullPath("../local3d/desert/sorties/kit/selection.json");if(!File.Exists(chemin))throw Faux("sélection absente : "+chemin);
            var planche=JsonUtility.FromJson<Selection>(File.ReadAllText(chemin))?.planche??new Rangee[0];
            var rangees=Finis.Select(f=>planche.FirstOrDefault(r=>r!=null&&r.fini==f)??throw Faux("rangée absente de selection.json : "+f)).ToArray();
            foreach(var r in rangees)if(r.etapes==null||r.etapes.Length!=3||r.etapes[2]!=r.fini)throw Faux(r.fini+" : étapes ["+string.Join(",",r.etapes??new string[0])+"] ; attendu trois, la dernière le fini");
            var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");var terrain=ville.outil&&ville.outil.roads?ville.outil.roads.terrain:null;if(!terrain)throw Faux("pas de terrain");
            ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            // Chaque pièce instanciée à l'origine, sans rotation, LOD0 forcé : son enveloppe se lit avant la pose.
            var racine=new GameObject("Lot 905 : galerie de l'enceinte").transform;var pieces=new List<(GameObject o,int r,int c,Bounds b)>();
            for(int r=0;r<3;r++)for(int c=seuls?2:0;c<3;c++)
            {
                string id=rangees[r].etapes[c];var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/ForgeLocal3D/Desert/Prefabs/"+id+".prefab");if(!prefab)throw Faux("prefab absent : "+id);
                var o=Object.Instantiate(prefab,Vector3.zero,Quaternion.identity,racine);o.name=id;var g=o.GetComponent<LODGroup>();if(g)g.ForceLOD(0);
                var lod=Lod0(o);if(Actifs(o)==0)throw Faux(id+" : aucun renderer actif au LOD0");var b=lod[0].bounds;foreach(var x in lod)b.Encapsulate(x.bounds);pieces.Add((o,r,c,b));
            }
            // Les pas de la grille se tirent des trois pièces finies : la plus large + 6 m ; la plus profonde + la plus haute.
            var finis=pieces.Where(p=>p.c==2).Select(p=>p.b.size).ToArray();float pasC=finis.Max(s=>s.x)+6f,pasR=finis.Max(s=>s.z)+finis.Max(s=>s.y);
            int colonnes=seuls?1:3;float largeur=colonnes*pasC,profondeur=3*pasR;
            // Au bord de la ville de 1400, à 20 m de la dernière maison, du côté où le sol de la galerie est le plus plat (méthode du lot 779).
            var tr=ville.outil.Maisons?.Racine;if(!tr||tr.childCount==0)throw Faux("aucune maison de 1400 au bord de laquelle poser");
            var bo=new Bounds(tr.GetChild(0).position,Vector3.zero);foreach(Transform t in tr)bo.Encapsulate(t.position);
            float Relief(Vector3 p){var h=Enumerable.Range(0,35).Select(i=>terrain.SampleHeight(p+new Vector3((i%7/6f-.5f)*largeur,0,(i/7/4f-.5f)*profondeur))).ToArray();return h.Max()-h.Min();}
            var centre=new[]{new Vector3(bo.center.x,0,bo.max.z+20+profondeur/2),new Vector3(bo.center.x,0,bo.min.z-20-profondeur/2),new Vector3(bo.max.x+20+largeur/2,0,bo.center.z),new Vector3(bo.min.x-20-largeur/2,0,bo.center.z)}.OrderBy(Relief).First();
            // La caméra regarde vers -Z : la première colonne à gauche (+X), la première rangée au fond (-Z). Chaque pièce au sol sous son centre.
            var poses=pieces.Select(p=>{var pos=centre+new Vector3(((colonnes-1)/2f-(seuls?0:p.c))*pasC,0,(p.r-1)*pasR);pos.y=terrain.SampleHeight(pos)+terrain.transform.position.y;
                p.o.transform.position=pos;return (p.o,p.r,p.c,pos,b:new Bounds(p.b.center+pos,p.b.size));}).ToList();
            // Surplomb à 35°, cap 180 : les façades (+Z des prefabs) face à la caméra, qui recule par pas de 6 % jusqu'à tenir les huit coins de chaque pièce.
            camera.aspect=1600f/900f;bool Dans(Vector3 v){var q=camera.WorldToViewportPoint(v);return q.z>camera.nearClipPlane&&q.x>.02f&&q.x<.98f&&q.y>.02f&&q.y<.98f;}
            bool Tient(Bounds b)=>Enumerable.Range(0,8).All(i=>Dans(b.center+Vector3.Scale(b.extents,new Vector3(i%2*2-1,i/2%2*2-1,i/4*2-1))));
            bool cadre=false;for(float d=30f;d<=DesertCityCamera.DistanceMax&&!cadre;d*=1.06f){ville.Poser(centre,180f,35f,d);cadre=poses.All(p=>Tient(p.b));}
            if(!cadre)throw Faux("pièces hors du cadre à "+N(ville.Distance)+" m : "+string.Join(", ",poses.Where(p=>!Tient(p.b)).Select(p=>p.o.name)));
            for(int i=0;i<10;i++)yield return null;
            string bilan="{\"pieces\":["+string.Join(",",poses.Select(p=>"{\"id\":\""+p.o.name+"\",\"rangee\":"+p.r+",\"colonne\":"+p.c+",\"position\":"+V(p.pos)
                +",\"enveloppe\":{\"min\":"+V(p.b.min)+",\"max\":"+V(p.b.max)+"},\"renderers\":"+Actifs(p.o)+"}"))+"],\"nombre_pieces\":"+poses.Count+"}";
            File.WriteAllText(rapport,bilan);Debug.Log("CAPTURE_905 "+bilan);
        }
    }
}
