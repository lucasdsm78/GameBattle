import { useCallback, useState } from 'react';
import { AccountBar } from '../components/AccountBar';
import { CreateRoomCard } from '../components/CreateRoomCard';
import { JoinRoomCard } from '../components/JoinRoomCard';
import { useRoom } from '../hooks/useRoom';
import { Route } from '../hooks/useRoute';
import { Account } from '../services/accountsApi';
import { Room } from '../services/roomsApi';
import { InvitationScreen } from './InvitationScreen';
import { RoomLobby } from './RoomLobby';

type Props = {
  account: Account;
  route: Route;
  navigate: (route: Route, options?: { replace?: boolean }) => void;
  onSignOut: () => Promise<void>;
  onSessionLost: () => void;
};

/** L'espace du joueur connecté : son salon s'il en a un, sinon de quoi en créer ou en rejoindre un. */
export function PlayerArea({ account, route, navigate, onSignOut, onSessionLost }: Props) {
  const { state, entered, leave, resume, reload } = useRoom(onSessionLost);
  const [publicRequest, setPublicRequest] = useState(0);
  const home = useCallback(() => navigate({ name: 'home' }, { replace: true }), [navigate]);
  const joined = useCallback(
    (room: Room) => {
      entered(room);
      home();
    },
    [entered, home],
  );

  let content;
  if (route.name === 'invitation') {
    content = <InvitationScreen code={route.code} roomState={state} onJoined={joined} onLeaveCurrent={leave} onDone={home} />;
  } else if (state.status === 'loading') {
    content = (
      <section className="panel status-card is-loading" aria-busy="true" aria-label="Chargement de ta partie">
        <span className="loader" />
      </section>
    );
  } else if (state.status === 'unreachable') {
    content = (
      <section className="panel status-card" role="alert">
        <h2 className="status-title">Connexion impossible</h2>
        <p className="welcome-text">{state.message}</p>
        <button type="button" className="primary-button" onClick={reload}>
          Réessayer
        </button>
      </section>
    );
  } else if (state.status === 'in-room') {
    content = <RoomLobby room={state.room} link={state.link} onRoom={entered} onLeave={leave} onResume={resume} />;
  } else {
    content = (
      <>
        {state.notice ? (
          <p className="notice" role="status">
            {state.notice}
          </p>
        ) : null}
        <div className="play-grid">
          <JoinRoomCard
            onJoined={entered}
            onInvitation={(code) => navigate({ name: 'invitation', code })}
            onCreatePublic={() => setPublicRequest((count) => count + 1)}
          />
          <CreateRoomCard onCreated={entered} publicRequest={publicRequest} />
        </div>
      </>
    );
  }

  return (
    <main className="arena">
      <AccountBar account={account} onSignOut={onSignOut} />
      {content}
    </main>
  );
}
