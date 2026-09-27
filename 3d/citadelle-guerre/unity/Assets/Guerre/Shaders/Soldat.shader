// Soldat animé par texture de sommets (VAT) : la marche et le repos, cuits dans
// Blender, sont rejoués ici. Chaque homme porte son état d'animation (_AnimEtat)
// et la couleur de son camp (_BaseColor), propres à chaque instance d'Entities Graphics.
//   _AnimEtat.x : phase de marche (0..1)   .y : poids de la marche (0 : repos, 1 : marche)
//   _AnimEtat.z : décalage du repos (0..1), pour que les hommes ne respirent pas ensemble
//   _AnimEtat.w : -1 pour un homme tombé, qui garde la pose de repos, immobile
//   _AnimCombat.x : phase du coup (0..1)   .y : poids de la garde (0 : hors combat, 1 : en garde)
//   _AnimCombat.z : poids de la posture à l'abri, à genou derrière son pavois ; pour le cavalier, poids du galop
//                   de charge, lance couchée, joué au pas de la marche (_AbriSuitLaMarche)
// Texture _VAT : ligne = image ; colonne i = position du coin i, colonne i + Coins = sa normale.
Shader "Guerre/Soldat"
{
    Properties
    {
        _BaseColor ("Couleur du camp", Color) = (1, 1, 1, 1)
        _AnimEtat ("État d'animation", Vector) = (0, 0, 0, 0)
        _AnimCombat ("État de combat", Vector) = (0, 0, 0, 0)
        [NoScaleOffset] _VAT ("Animation cuite", 2D) = "black" {}
        _Coins ("Coins", Float) = 0
        _ImagesMarche ("Images de marche", Float) = 24
        _ImagesRepos ("Images de repos", Float) = 24
        _DureeRepos ("Durée du repos (s)", Float) = 4
        _ImagesCombat ("Images de combat", Float) = 24
        _ImagesAbri ("Images à l'abri", Float) = 12
        _DureeAbri ("Durée à l'abri (s)", Float) = 3
        _AbriSuitLaMarche ("Galop au pas de la marche", Float) = 0
        _VATActif ("Animation active", Float) = 1
    }

    HLSLINCLUDE
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

    CBUFFER_START(UnityPerMaterial)
        float4 _BaseColor;
        float4 _AnimEtat;
        float4 _AnimCombat;
        float _Coins, _ImagesMarche, _ImagesRepos, _DureeRepos, _ImagesCombat, _ImagesAbri, _DureeAbri, _VATActif, _AbriSuitLaMarche;
    CBUFFER_END

    #ifdef UNITY_DOTS_INSTANCING_ENABLED
        UNITY_DOTS_INSTANCING_START(MaterialPropertyMetadata)
            UNITY_DOTS_INSTANCED_PROP(float4, _BaseColor)
            UNITY_DOTS_INSTANCED_PROP(float4, _AnimEtat)
            UNITY_DOTS_INSTANCED_PROP(float4, _AnimCombat)
        UNITY_DOTS_INSTANCING_END(MaterialPropertyMetadata)
        #define _BaseColor UNITY_ACCESS_DOTS_INSTANCED_PROP_WITH_DEFAULT(float4, _BaseColor)
        #define _AnimEtat  UNITY_ACCESS_DOTS_INSTANCED_PROP_WITH_DEFAULT(float4, _AnimEtat)
        #define _AnimCombat UNITY_ACCESS_DOTS_INSTANCED_PROP_WITH_DEFAULT(float4, _AnimCombat)
    #endif

    TEXTURE2D(_VAT);

    struct Attributes
    {
        float3 positionOS : POSITION;
        float3 normalOS   : NORMAL;
        float4 color      : COLOR;
        uint   vertexID   : SV_VertexID;
        UNITY_VERTEX_INPUT_INSTANCE_ID
    };

    // Une image de l'animation, interpolée entre deux lignes cuites.
    void Echantillon(uint id, float ligne0, float images, float phase, out float3 p, out float3 n)
    {
        float f = frac(phase) * images;
        uint a = (uint)floor(f), b = (a + 1) % (uint)images;
        float t = f - floor(f);
        uint c = (uint)_Coins;
        p = lerp(LOAD_TEXTURE2D_LOD(_VAT, uint2(id, ligne0 + a), 0).xyz, LOAD_TEXTURE2D_LOD(_VAT, uint2(id, ligne0 + b), 0).xyz, t);
        n = lerp(LOAD_TEXTURE2D_LOD(_VAT, uint2(id + c, ligne0 + a), 0).xyz, LOAD_TEXTURE2D_LOD(_VAT, uint2(id + c, ligne0 + b), 0).xyz, t);
    }

    void Animer(Attributes v, out float3 positionOS, out float3 normalOS)
    {
        positionOS = v.positionOS; normalOS = v.normalOS;
        float4 etat = _AnimEtat;
        if (_VATActif < 0.5 || etat.w < -0.5) return;
        float4 combat = _AnimCombat;
        float3 pm, nm, pr, nr, pc, nc;
        Echantillon(v.vertexID, 0, _ImagesMarche, etat.x, pm, nm);
        Echantillon(v.vertexID, _ImagesMarche, _ImagesRepos, etat.z + _Time.y / _DureeRepos, pr, nr);
        positionOS = lerp(pr, pm, etat.y);
        normalOS = lerp(nr, nm, etat.y);
        if (combat.y > 0.001)
        {
            Echantillon(v.vertexID, _ImagesMarche + _ImagesRepos, _ImagesCombat, combat.x, pc, nc);
            positionOS = lerp(positionOS, pc, combat.y);
            normalOS = lerp(normalOS, nc, combat.y);
        }
        if (combat.z > 0.001)
        {
            float3 pa, na;
            float phaseAbri = _AbriSuitLaMarche > 0.5 ? etat.x : etat.z + _Time.y / _DureeAbri;
            Echantillon(v.vertexID, _ImagesMarche + _ImagesRepos + _ImagesCombat, _ImagesAbri, phaseAbri, pa, na);
            positionOS = lerp(positionOS, pa, combat.z);
            normalOS = lerp(normalOS, na, combat.z);
        }
        normalOS = normalize(normalOS);
    }
    ENDHLSL

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ DOTS_INSTANCING_ON
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile _ _FORWARD_PLUS
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS   : TEXCOORD1;
                float3 albedo     : TEXCOORD2;
                float  fog        : TEXCOORD3;
            };

            Varyings Vert(Attributes v)
            {
                UNITY_SETUP_INSTANCE_ID(v);
                Varyings o;
                float3 p, n;
                Animer(v, p, n);
                o.positionWS = TransformObjectToWorld(p);
                o.normalWS = TransformObjectToWorldNormal(n);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                // Les zones marquées (alpha 1) prennent la couleur du camp.
                o.albedo = v.color.rgb * lerp(float3(1, 1, 1), _BaseColor.rgb, v.color.a);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                Light soleil = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                float3 direct = soleil.color * saturate(dot(n, soleil.direction)) * soleil.shadowAttenuation;
                float3 c = i.albedo * (direct + SampleSH(n));
                return half4(MixFog(c, i.fog), 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ DOTS_INSTANCING_ON
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
            float3 _LightDirection;
            float3 _LightPosition;

            float4 Vert(Attributes v) : SV_POSITION
            {
                UNITY_SETUP_INSTANCE_ID(v);
                float3 p, n;
                Animer(v, p, n);
                float3 pw = TransformObjectToWorld(p), nw = TransformObjectToWorldNormal(n);
                #if _CASTING_PUNCTUAL_LIGHT_SHADOW
                    float3 dir = normalize(_LightPosition - pw);
                #else
                    float3 dir = _LightDirection;
                #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(pw, nw, dir));
                #if UNITY_REVERSED_Z
                    cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
                #else
                    cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
                #endif
                return cs;
            }
            half4 Frag() : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ DOTS_INSTANCING_ON
            float4 Vert(Attributes v) : SV_POSITION
            {
                UNITY_SETUP_INSTANCE_ID(v);
                float3 p, n;
                Animer(v, p, n);
                return TransformObjectToHClip(p);
            }
            half4 Frag() : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ DOTS_INSTANCING_ON
            struct V { float4 cs : SV_POSITION; float3 n : TEXCOORD0; };
            V Vert(Attributes v)
            {
                UNITY_SETUP_INSTANCE_ID(v);
                float3 p, n;
                Animer(v, p, n);
                V o; o.cs = TransformObjectToHClip(p); o.n = TransformObjectToWorldNormal(n);
                return o;
            }
            half4 Frag(V i) : SV_Target { return half4(normalize(i.n), 0); }
            ENDHLSL
        }
    }
}
