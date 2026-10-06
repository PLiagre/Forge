using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 362 : les parcelles du plan tracées au sol, sur le terrain du moment (la copie où les rues sont
    // posées). Un ruban suit le contour tel que le plan le donne, sans le corriger. En chantier, un cordeau
    // tendu sur un piquet à chaque coin ; achevée, une borne à chaque coin. Rien n'est décidé ici : l'état
    // se lit dans `EnChantier`. Le terrain n'est jamais touché. Pas un composant : la scène ne change pas.
    public sealed class DesertParcelles
    {
        const float DemiRuban=.10f,AuDessusRuban=.03f,PasRuban=.5f;
        static readonly Vector3 TaillePiquet=new(.06f,.8f,.06f),TailleBorne=new(.3f,.5f,.3f);
        const float CentrePiquet=.35f,HauteurCordeau=.6f,EpaisseurCordeau=.03f,CentreBorne=.15f;

        public Transform Racine{get;}
        // SHA-256 de la description du dernier dessin : une ligne par parcelle, dans l'ordre du plan.
        public string Empreinte{get;private set;}=Hacher("");
        readonly Terrain terrain;
        readonly Material rubanChantier,rubanAcheve,piquet,cordeau,borne;

        public DesertParcelles(Transform parent,Terrain terrain)
        {
            var defaut=GraphicsSettings.currentRenderPipeline?GraphicsSettings.currentRenderPipeline.defaultMaterial:null;
            if(!defaut)throw new InvalidOperationException("Pas de matériau par défaut du pipeline de rendu : les parcelles ne sont pas dessinées.");
            Material M(string nom,float r,float g,float b)=>new Material(defaut){name=nom,color=new Color(r,g,b)};
            rubanChantier=M("Ruban de chantier",.50f,.38f,.26f);rubanAcheve=M("Ruban achevé",.93f,.91f,.86f);
            piquet=M("Piquet",.30f,.20f,.12f);cordeau=M("Cordeau",.55f,.33f,.18f);borne=M("Borne",.90f,.88f,.82f);
            this.terrain=terrain;
            var go=new GameObject("Parcelles du plan");go.transform.SetParent(parent,false);Racine=go.transform;
        }

        float Sol(Vector3 p)=>terrain.SampleHeight(p)+terrain.transform.position.y;
        // Repère du lot 293 : (x, y) du plan devient (-x, sol, -y).
        Vector3 Monde(PointLocal p){var v=new Vector3((float)-p.X,0,(float)-p.Y);v.y=Sol(v);return v;}

        public List<(long identifiant,string etat,string message)> Dessiner(IReadOnlyList<ParcelleDuPlan> parcelles)
        {
            // D'abord vider : un Destroy différé laisserait les anciennes parcelles comptées dans la même image.
            for(int i=Racine.childCount-1;i>=0;i--)
            {
                var enfant=Racine.GetChild(i).gameObject;var filtre=enfant.GetComponent<MeshFilter>();
                if(filtre&&filtre.sharedMesh)Object.DestroyImmediate(filtre.sharedMesh);
                Object.DestroyImmediate(enfant);
            }
            var resultats=new List<(long identifiant,string etat,string message)>();var description=new StringBuilder();
            float limite=terrain.terrainData.size.x/2-1;
            foreach(var p in parcelles)
            {
                string id=p.Identifiant.ToString(CultureInfo.InvariantCulture);
                if(description.Length>0)description.Append('\n');
                if(p.Contour.Any(c=>Math.Abs(c.X)>limite||Math.Abs(c.Y)>limite))
                {
                    resultats.Add((p.Identifiant,"refusee","Parcelle "+id+" hors du terrain : non dessinée."));
                    description.Append(id).Append(" refusee");continue;
                }
                string etat=p.EnChantier?"cordeau":"bornes";
                description.Append(id).Append(' ').Append(etat);
                var go=new GameObject("Parcelle "+id);go.transform.SetParent(Racine,false);
                var coins=p.Contour.Select(Monde).ToArray();int n=coins.Length;
                var pieces=new List<Transform>();
                if(p.EnChantier)
                {
                    foreach(var c in coins)pieces.Add(Cube("Piquet",go.transform,piquet,TaillePiquet,c+Vector3.up*CentrePiquet,Quaternion.identity));
                    for(int i=0;i<n;i++)
                    {
                        Vector3 a=coins[i]+Vector3.up*HauteurCordeau,b=coins[(i+1)%n]+Vector3.up*HauteurCordeau;
                        var t=Cube("Cordeau",go.transform,cordeau,new Vector3(EpaisseurCordeau,EpaisseurCordeau,Vector3.Distance(a,b)),(a+b)/2,Quaternion.identity);
                        t.LookAt(b);pieces.Add(t);
                    }
                }
                else for(int i=0;i<n;i++)
                {
                    var axe=Horizontal(coins[(i+1)%n]-coins[i]);
                    pieces.Add(Cube("Borne",go.transform,borne,TailleBorne,coins[i]+Vector3.up*CentreBorne,axe==Vector3.zero?Quaternion.identity:Quaternion.LookRotation(axe)));
                }
                var (sommets,triangles)=Ruban(coins);
                var maillage=new Mesh{name="Ruban "+id};
                maillage.SetVertices(sommets.Select(go.transform.InverseTransformPoint).ToArray());
                maillage.SetTriangles(triangles,0);maillage.RecalculateNormals();maillage.RecalculateBounds();
                go.AddComponent<MeshFilter>().sharedMesh=maillage;
                go.AddComponent<MeshRenderer>().sharedMaterial=p.EnChantier?rubanChantier:rubanAcheve;
                foreach(var t in pieces)Ecrire(description,t.position);
                foreach(var s in sommets)Ecrire(description,s);
                resultats.Add((p.Identifiant,etat,""));
            }
            Empreinte=Hacher(description.ToString());
            return resultats;
        }

        static Vector3 Horizontal(Vector3 v){v.y=0;return v.sqrMagnitude>1e-12f?v.normalized:Vector3.zero;}

        // Chaque côté, du coin i au coin i+1 (le dernier vers le premier), échantillonné à pas égaux d'au plus
        // 0,5 m, ses deux bouts compris : deux sommets par échantillon, à ±0,10 m de l'axe, chacun au sol lu
        // sous lui-même + 0,03 m (sur une pente en travers, le bord amont n'est pas enterré).
        // Deux triangles par pas, tournés vers le ciel ; un côté n'est pas joint au suivant.
        (List<Vector3> sommets,int[] triangles) Ruban(Vector3[] coins)
        {
            var sommets=new List<Vector3>();var triangles=new List<int>();int n=coins.Length;
            for(int i=0;i<n;i++)
            {
                Vector3 a=coins[i],b=coins[(i+1)%n];var axe=Horizontal(b-a);var travers=new Vector3(-axe.z,0,axe.x)*DemiRuban;
                float longueur=Vector2.Distance(new Vector2(a.x,a.z),new Vector2(b.x,b.z));int pas=Mathf.Max(1,Mathf.CeilToInt(longueur/PasRuban-1e-4f));
                int debut=sommets.Count;
                for(int k=0;k<=pas;k++)
                {
                    var q=Vector3.Lerp(a,b,(float)k/pas);
                    foreach(var s in new[]{q+travers,q-travers}){var v=s;v.y=Sol(v)+AuDessusRuban;sommets.Add(v);}
                }
                for(int k=0;k<pas;k++){int g=debut+2*k;triangles.AddRange(new[]{g,g+2,g+1,g+1,g+2,g+3});}
            }
            return (sommets,triangles.ToArray());
        }

        Transform Cube(string nom,Transform parent,Material materiau,Vector3 taille,Vector3 position,Quaternion rotation)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=nom;
            Object.DestroyImmediate(go.GetComponent<Collider>());
            go.GetComponent<MeshRenderer>().sharedMaterial=materiau;
            var t=go.transform;t.SetParent(parent,false);t.SetPositionAndRotation(position,rotation);t.localScale=taille;
            return t;
        }

        static void Ecrire(StringBuilder s,Vector3 v)
        {
            foreach(var c in new[]{v.x,v.y,v.z})s.Append(' ').Append(c.ToString("F2",CultureInfo.InvariantCulture));
        }

        static string Hacher(string texte)
        {
            using var sha=SHA256.Create();
            return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(texte)).Select(b=>b.ToString("x2")));
        }
    }
}
