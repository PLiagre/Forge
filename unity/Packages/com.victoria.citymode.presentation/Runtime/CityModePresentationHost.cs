using System;
using UnityEngine;
using Victoria.CityMode.Integration;

namespace Victoria.CityMode.Presentation
{
    /// <summary>
    /// Receives lifecycle notifications from the host-owned presentation root.
    /// Implementations render authoritative snapshots and never own simulation state.
    /// </summary>
    public interface ICityModePresentationView
    {
        void Open(CityLaunchContext context);
        void Present(CitySnapshotEnvelope snapshot);
        void CompleteIntent(CityIntentReceipt receipt);
        void Close();
    }

    /// <summary>
    /// Thin Unity lifecycle for a CityModeSession. It has no automatic bootstrap,
    /// scene dependency, fixture, local clock, simulation, or persistence service.
    /// The ForgeHistory host explicitly creates and destroys exactly one instance.
    /// </summary>
    public sealed class CityModePresentationHost : MonoBehaviour, IDisposable
    {
        static CityModePresentationHost active;

        CityModeSession session;
        ICityModePresentationView view;
        bool disposed;

        public CityLaunchContext Context => session != null ? session.Context : null;
        public CitySnapshotEnvelope CurrentSnapshot =>
            session != null ? session.CurrentSnapshot : null;
        public bool IsBound => session != null && !disposed && !session.IsDisposed;
        public static bool HasActiveInstance => active != null && active.IsBound;

        public static bool TryCreate(
            CityModeSession hostSession,
            out CityModePresentationHost presentation,
            out CityModeErrorCode error)
        {
            presentation = null;
            if (hostSession == null || hostSession.IsDisposed)
                return Fail(CityModeErrorCode.HostUnavailable, out error);
            if (active != null && active.IsBound)
                return Fail(CityModeErrorCode.SessionAlreadyActive, out error);

            var root = new GameObject("City Mode Presentation [" +
                hostSession.Context.cityId + "]");
            var candidate = root.AddComponent<CityModePresentationHost>();
            candidate.session = hostSession;
            active = candidate;
            presentation = candidate;
            error = CityModeErrorCode.None;
            return true;
        }

        public bool TryAttachView(
            ICityModePresentationView presentationView,
            out CityModeErrorCode error)
        {
            if (!IsBound)
                return Fail(CityModeErrorCode.HostUnavailable, out error);
            if (presentationView == null || view != null)
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            try
            {
                presentationView.Open(session.Context);
                presentationView.Present(session.CurrentSnapshot);
            }
            catch
            {
                try
                {
                    presentationView.Close();
                }
                catch
                {
                    // A failed view is never retained by the host.
                }
                return Fail(CityModeErrorCode.InternalError, out error);
            }
            view = presentationView;
            error = CityModeErrorCode.None;
            return true;
        }

        public bool TryRefreshSnapshot(out CityModeErrorCode error)
        {
            if (!IsBound)
                return Fail(CityModeErrorCode.HostUnavailable, out error);
            if (!session.TryRefreshSnapshot(out error))
                return false;
            if (view == null)
                return true;
            try
            {
                view.Present(session.CurrentSnapshot);
                return true;
            }
            catch
            {
                return Fail(CityModeErrorCode.InternalError, out error);
            }
        }

        public bool TrySubmitIntent(
            CityIntentEnvelope intent,
            out CityIntentReceipt receipt,
            out CityModeErrorCode error)
        {
            receipt = null;
            if (!IsBound)
                return Fail(CityModeErrorCode.HostUnavailable, out error);
            var accepted = session.TrySubmitIntent(intent, out receipt, out error);
            if (view == null || receipt == null)
                return accepted;
            try
            {
                view.CompleteIntent(receipt);
                return accepted;
            }
            catch
            {
                return Fail(CityModeErrorCode.InternalError, out error);
            }
        }

        public void Dispose()
        {
            if (disposed)
                return;
            var root = gameObject;
            Release();
            if (root == null)
                return;
            if (Application.isPlaying)
                Destroy(root);
            else
                DestroyImmediate(root);
        }

        void OnDestroy()
        {
            Release();
        }

        void Release()
        {
            if (disposed)
                return;
            disposed = true;
            if (view != null)
            {
                try
                {
                    view.Close();
                }
                catch
                {
                    // Destruction must remain idempotent even if a view fails to close.
                }
                view = null;
            }
            session = null;
            if (ReferenceEquals(active, this))
                active = null;
        }

        static bool Fail(CityModeErrorCode value, out CityModeErrorCode error)
        {
            error = value;
            return false;
        }
    }
}
