// L'encre d'un nom écrit sur la carte, et le halo clair qui la détache du relief. Chaque lettre est un carré de
// l'atlas de la police, dont seule la couverture (alpha) est lue. Le même maillage se dessine deux fois, par deux
// matériaux : d'abord le halo de toutes les lettres (`_Halo` à 1), puis leur encre (`_Halo` à 0), pour que le halo
// d'une lettre ne morde jamais l'encre de sa voisine. Le halo est la lettre épaissie : la couverture la plus forte
// lue autour du point, pleine à mi-rayon, plus légère au rayon. Le carré d'une lettre déborde de son dessin pour
// porter ce halo ; `cadre` borne ce qui est lu à la lettre elle-même, sans quoi ses voisines dans l'atlas
// baveraient dans son halo. Par sommet : l'opacité du nom (alpha) et la force de son halo (rouge), et le rayon du
// halo en texels de l'atlas. Le nom est imprimé sur le terrain : dessiné juste après lui et avant tout objet posé
// sur la carte, sans lire ni écrire la profondeur. Aucun pli du relief ne le coupe, et une ville ou une armée passe
// devant lui.
Shader "Forge/NomDeCarte"
{
    Properties
    {
        [NoScaleOffset] _MainTex("Atlas de la police", 2D) = "white" {}
        _Teinte("Teinte de l'encre, ou du halo", Color) = (0.1, 0.08, 0.06, 1)
        _Halo("0 : l'encre ; 1 : le halo", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry-5" "IgnoreProjector" = "True" }
        Pass
        {
            Name "Nom" Tags { "LightMode" = "UniversalForward" }
            Cull Off ZWrite Off ZTest Always Blend SrcAlpha OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_TexelSize, _Teinte; float _Halo;
            CBUFFER_END
            TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
            struct A { float3 p : POSITION; float2 uv : TEXCOORD0; float4 cadre : TEXCOORD1; float2 rayon : TEXCOORD2; float4 c : COLOR; };
            struct V { float4 clip : SV_POSITION; float2 uv : TEXCOORD0; float4 cadre : TEXCOORD1; float3 reglage : TEXCOORD2; };
            V Vert(A a) { V o; o.clip = TransformObjectToHClip(a.p); o.uv = a.uv; o.cadre = a.cadre; o.reglage = float3(a.rayon.x, a.c.r, a.c.a); return o; }
            // Ce que la lettre couvre en ce point de l'atlas ; rien hors de son cadre.
            float Couverture(float2 uv, float4 cadre)
            {
                float dedans = step(cadre.x, uv.x) * step(cadre.y, uv.y) * step(uv.x, cadre.z) * step(uv.y, cadre.w);
                return SAMPLE_TEXTURE2D_LOD(_MainTex, sampler_MainTex, uv, 0).a * dedans;
            }
            static const float2 AUTOUR[8] = { float2(1, 0), float2(0.7071, 0.7071), float2(0, 1), float2(-0.7071, 0.7071), float2(-1, 0), float2(-0.7071, -0.7071), float2(0, -1), float2(0.7071, -0.7071) };
            half4 Frag(V i) : SV_Target
            {
                float ici = Couverture(i.uv, i.cadre);
                if (_Halo < 0.5) return half4(_Teinte.rgb, _Teinte.a * i.reglage.z * ici);
                float2 pas = _MainTex_TexelSize.xy * i.reglage.x; float pres = ici, loin = 0.0;
                for (int k = 0; k < 8; k++)
                {
                    pres = max(pres, Couverture(i.uv + AUTOUR[k] * pas * 0.5, i.cadre));
                    loin += Couverture(i.uv + AUTOUR[k] * pas, i.cadre);
                }
                float halo = max(pres, saturate(loin * 0.3));
                return half4(_Teinte.rgb, _Teinte.a * i.reglage.y * i.reglage.z * halo);
            }
            ENDHLSL
        }
    }
}
