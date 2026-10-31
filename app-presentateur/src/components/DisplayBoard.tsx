import { useEffect } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';
import { StopChronoBoard } from './StopChronoBoard';
import { CultureBoard } from './CultureBoard';
import { FinalRankingBoard } from './FinalRankingBoard';
import { BombeBoard } from './BombeBoard';
import { MemoryBoard } from './MemoryBoard';
import { SevenDifferencesBoard } from './SevenDifferencesBoard';
import { AuctionBoard } from './AuctionBoard';
import { ForbiddenWordBoard } from './ForbiddenWordBoard';
import { VanishingWordBoard } from './VanishingWordBoard';
import { FlashCalcBoard } from './FlashCalcBoard';
import { RightFlagBoard } from './RightFlagBoard';
import { GoldenFamilyBoard } from './GoldenFamilyBoard';
import { GameScreen } from './GameScreen';
import { BlindtestBoard } from './BlindtestBoard';

type Props = {
  gameConfig: GameConfigSnapshot | null;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  onBuzz: (team: string) => void;
  onStartChrono: () => void;
  onStopChrono: () => void;
  onCultureBuzz: (team: string) => void;
  onBombeBuzz: (team: string) => void;
  onBombeBeginAfterRoll: () => void;
  onBombeExplode: () => void;
  onSevenDifferencesOpen: () => void;
  onSevenDifferencesBuzz: (team: string) => void;
  onAuctionBuzz: (team: string) => void;
  onVanishingBuzz: (team: string) => void;
  onFlashCalcBuzz: (team: string) => void;
  onRightFlagBuzz: (team: string) => void;
  onGoldenFamilyBuzz: (team: string) => void;
};

const KEYBOARD_BINDINGS = ['1', '2', '3', '4', '5', '6'];

const normalizeKeyboardValue = (value: string): string => value.trim().toLowerCase().replace(/\s+/g, '');

const bindingAliases = (binding: string): string[] => {
  const normalized = normalizeKeyboardValue(binding);
  if (!normalized) {
    return [];
  }

  const aliases = new Set([normalized]);
  if (normalized.length === 1) {
    aliases.add(`digit${normalized}`);
    aliases.add(`numpad${normalized}`);
    aliases.add(`key${normalized}`);
  }

  const specialAliases: Record<string, string[]> = {
    space: ['space', 'spacebar', 'espace'],
    espace: ['space', 'spacebar', 'espace'],
    enter: ['enter', 'return', 'entree', 'entrée'],
    return: ['enter', 'return'],
    tab: ['tab', 'tabulation'],
    escape: ['escape', 'esc', 'echap', 'échap'],
    esc: ['escape', 'esc'],
    arrowup: ['arrowup', 'up', 'haut'],
    up: ['arrowup', 'up', 'haut'],
    arrowdown: ['arrowdown', 'down', 'bas'],
    down: ['arrowdown', 'down', 'bas'],
    arrowleft: ['arrowleft', 'left', 'gauche'],
    left: ['arrowleft', 'left', 'gauche'],
    arrowright: ['arrowright', 'right', 'droite'],
    right: ['arrowright', 'right', 'droite'],
  };

  for (const alias of specialAliases[normalized] ?? []) {
    aliases.add(alias);
  }

  return [...aliases];
};

const eventAliases = (event: KeyboardEvent): Set<string> => {
  const key = normalizeKeyboardValue(event.key === ' ' ? 'space' : event.key);
  const code = normalizeKeyboardValue(event.code);
  const compactCode = normalizeKeyboardValue(event.code.replace(/^(Key|Digit|Numpad|Arrow)/, ''));
  const aliases = new Set([key, code, compactCode]);

  if (event.code === 'Space') {
    aliases.add(' ');
    aliases.add('space');
    aliases.add('espace');
  }
  if (event.code === 'Enter') {
    aliases.add('enter');
    aliases.add('return');
  }

  return aliases;
};

const matchesBinding = (event: KeyboardEvent, binding: string): boolean => {
  const aliases = eventAliases(event);
  return bindingAliases(binding).some((candidate) => aliases.has(candidate));
};

export function DisplayBoard({
  gameConfig,
  connectionState,
  errorMessage,
  onBuzz,
  onStartChrono,
  onStopChrono,
  onCultureBuzz,
  onBombeBuzz,
  onBombeBeginAfterRoll,
  onBombeExplode,
  onSevenDifferencesOpen,
  onSevenDifferencesBuzz,
  onAuctionBuzz,
  onVanishingBuzz,
  onFlashCalcBuzz,
  onRightFlagBuzz,
  onGoldenFamilyBuzz,
}: Props) {
  const chronoPhase = gameConfig?.session.stopchrono.phase;
  const chronoTeamIndex = gameConfig?.session.stopchrono.current_team_index;
  const culturePhase = gameConfig?.session.culture.phase;
  const cultureTiebreakTeams = gameConfig?.session.culture.tiebreak_teams;
  const bombePhase = gameConfig?.session.bombe.phase;
  const bombeTeamIndex = gameConfig?.session.bombe.current_team_index;
  const sevenDifferencesPhase = gameConfig?.session.seven_differences.phase;
  const sevenDifferencesBlockedTeam = gameConfig?.session.seven_differences.blocked_team;
  const auctionPhase = gameConfig?.session.auction.phase;
  const auctionActiveTeam = gameConfig?.session.auction.active_team;
  const vanishingPhase = gameConfig?.session.vanishing_word.phase;
  const vanishingExcludedTeams = gameConfig?.session.vanishing_word.excluded_teams;
  const flashCalcPhase = gameConfig?.session.flash_calc.phase;
  const rightFlagPhase = gameConfig?.session.right_flag.phase;
  const goldenFamilyPhase = gameConfig?.session.golden_family.phase;
  const activeGameKey = gameConfig?.session.active_round?.game_key ?? 'blindtest';

  useEffect(() => {
    if (!gameConfig?.settings.teams.length) {
      return;
    }

    const teams = gameConfig.settings.teams;
    const buzzerKeys = gameConfig.settings.buzzer_keys?.length
      ? gameConfig.settings.buzzer_keys
      : KEYBOARD_BINDINGS.slice(0, teams.length);

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) {
        return;
      }

      // Stop Chrono : seule la touche de l'équipe en cours (ou Espace) démarre puis arrête le chrono.
      if (activeGameKey === 'stopchrono') {
        const currentKey = buzzerKeys[chronoTeamIndex ?? 0] ?? '';
        if (!matchesBinding(event, currentKey) && !matchesBinding(event, 'space')) {
          return;
        }
        if (chronoPhase === 'idle') {
          onStartChrono();
        } else if (chronoPhase === 'running') {
          onStopChrono();
        }
        return;
      }

      // Culture générale : les touches d'équipe buzzent (uniquement quand une question est affichée).
      if (activeGameKey === 'culture') {
        if (culturePhase !== 'question') {
          return;
        }
        for (let index = 0; index < teams.length; index += 1) {
          if (matchesBinding(event, buzzerKeys[index] ?? '')) {
            // Pendant le départage, seules les équipes à égalité peuvent buzzer.
            if (!cultureTiebreakTeams?.length || cultureTiebreakTeams.includes(teams[index])) onCultureBuzz(teams[index]);
            return;
          }
        }
        return;
      }

      if (activeGameKey === 'bombe') {
        if (bombePhase !== 'running' && bombePhase !== 'awaiting_roll') return;
        const currentIndex = bombeTeamIndex ?? 0;
        if (matchesBinding(event, buzzerKeys[currentIndex] ?? '')) {
          onBombeBuzz(teams[currentIndex]);
        }
        return;
      }

      if (activeGameKey === 'seven_differences') {
        if (sevenDifferencesPhase !== 'open') return;
        for (let index = 0; index < teams.length; index += 1) {
          if (teams[index] !== sevenDifferencesBlockedTeam && matchesBinding(event, buzzerKeys[index] ?? '')) {
            onSevenDifferencesBuzz(teams[index]);
            return;
          }
        }
        return;
      }

      if (activeGameKey === 'auction') {
        if (auctionPhase !== 'bidding' && auctionPhase !== 'running') return;
        for (let index = 0; index < teams.length; index += 1) {
          if (
            matchesBinding(event, buzzerKeys[index] ?? '')
            && (auctionPhase === 'bidding' || teams[index] === auctionActiveTeam)
          ) {
            onAuctionBuzz(teams[index]);
            return;
          }
        }
        return;
      }

      // Le mot interdit se pilote uniquement depuis le téléphone de l'orateur.
      if (activeGameKey === 'forbidden_word') return;

      if (activeGameKey === 'vanishing_word') {
        if (vanishingPhase !== 'vanished') return;
        const index = teams.findIndex((team, position) => matchesBinding(event, buzzerKeys[position] ?? ''));
        if (index >= 0 && !vanishingExcludedTeams?.includes(teams[index])) onVanishingBuzz(teams[index]);
        return;
      }

      // Une famille en or : les buzzers ne servent qu'au face-à-face.
      if (activeGameKey === 'golden_family') {
        if (goldenFamilyPhase !== 'faceoff') return;
        const index = teams.findIndex((team, position) => matchesBinding(event, buzzerKeys[position] ?? ''));
        if (index >= 0) onGoldenFamilyBuzz(teams[index]);
        return;
      }

      // Jeux « buzze seulement si… » : toutes les équipes peuvent buzzer pendant le défilement.
      const streamBuzz = { flash_calc: [flashCalcPhase, onFlashCalcBuzz], right_flag: [rightFlagPhase, onRightFlagBuzz] } as const;
      if (activeGameKey === 'flash_calc' || activeGameKey === 'right_flag') {
        const [phase, buzz] = streamBuzz[activeGameKey];
        if (phase !== 'running') return;
        const index = teams.findIndex((team, position) => matchesBinding(event, buzzerKeys[position] ?? ''));
        if (index >= 0) buzz(teams[index]);
        return;
      }

      for (let index = 0; index < teams.length; index += 1) {
        if (matchesBinding(event, buzzerKeys[index] ?? '')) {
          onBuzz(teams[index]);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    culturePhase,
    cultureTiebreakTeams,
    bombePhase,
    bombeTeamIndex,
    onCultureBuzz,
    onBombeBuzz,
    onSevenDifferencesBuzz,
    onAuctionBuzz,
    onVanishingBuzz,
    vanishingPhase,
    vanishingExcludedTeams,
    onFlashCalcBuzz,
    flashCalcPhase,
    onRightFlagBuzz,
    rightFlagPhase,
    onGoldenFamilyBuzz,
    goldenFamilyPhase,
    gameConfig?.settings.buzzer_keys,
    gameConfig?.settings.teams,
    activeGameKey,
    chronoPhase,
    chronoTeamIndex,
    onBuzz,
    onStartChrono,
    onStopChrono,
    sevenDifferencesBlockedTeam,
    sevenDifferencesPhase,
    auctionActiveTeam,
    auctionPhase,
  ]);

  if (!gameConfig) {
    return (
      <main className="screen empty-state">
        <div className="panel waiting-card">
          <div className="show-logo show-logo-large" aria-label="GameBattle">
            <span>Game</span>
            <b>Battle</b>
          </div>
          <h1>{connectionState === 'disconnected' ? 'Connexion perdue' : 'Le plateau se prépare…'}</h1>
          <p>Le présentateur prépare la soirée : l’écran se synchronisera automatiquement.</p>
          {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
        </div>
      </main>
    );
  }

  if (gameConfig.status === 'finished') {
    return <FinalRankingBoard gameConfig={gameConfig} connectionState={connectionState} />;
  }

  const screen = { gameConfig, connectionState, errorMessage };
  const teamsOfGame = gameConfig.settings.teams;

  if (activeGameKey === 'stopchrono') {
    const chrono = gameConfig.session.stopchrono;
    return (
      <GameScreen
        {...screen}
        gameLabel="Stop Chrono"
        detail={`Tour ${chrono.round_number}/${chrono.rounds_total}`}
        className="chrono-screen"
        winnerTeam={chrono.winner_team}
        recap={teamsOfGame.map((team) => `${team} ${((chrono.total_errors_ms[team] ?? 0) / 1000).toFixed(2)} s`).join('  ·  ')}
      >
        <StopChronoBoard gameConfig={gameConfig} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'culture') {
    const culture = gameConfig.session.culture;
    return (
      <GameScreen {...screen} gameLabel="Culture générale" className="culture-screen" winnerTeam={culture.winner_team} scores={culture.scores}>
        <CultureBoard gameConfig={gameConfig} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'bombe') {
    return (
      <GameScreen {...screen} gameLabel="La Bombe" className="bombe-screen" winnerTeam={null}>
        <BombeBoard gameConfig={gameConfig} onBeginAfterRoll={onBombeBeginAfterRoll} onExplode={onBombeExplode} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'memory') {
    const memory = gameConfig.session.memory;
    return (
      <GameScreen
        {...screen}
        gameLabel="Mémoire en chaîne"
        className="memory-screen"
        winnerTeam={memory.winner_team}
        recap="Dernière équipe encore qualifiée"
      >
        <MemoryBoard memory={memory} teams={teamsOfGame} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'seven_differences') {
    const game = gameConfig.session.seven_differences;
    return (
      <GameScreen
        {...screen}
        gameLabel="Les 7 différences"
        className="seven-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <SevenDifferencesBoard gameConfig={gameConfig} onOpen={onSevenDifferencesOpen} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'auction') {
    const game = gameConfig.session.auction;
    return (
      <GameScreen
        {...screen}
        gameLabel="L’Enchère"
        detail="Première équipe à 20"
        className="auction-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <AuctionBoard gameConfig={gameConfig} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'vanishing_word') {
    const game = gameConfig.session.vanishing_word;
    return (
      <GameScreen
        {...screen}
        gameLabel="Le mot qui disparaît"
        detail={`Premier à ${game.winning_score}`}
        className="vw-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <VanishingWordBoard game={game} teams={gameConfig.settings.teams} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'flash_calc') {
    const game = gameConfig.session.flash_calc;
    return (
      <GameScreen
        {...screen}
        gameLabel="Calcul flash"
        detail={`Premier à ${game.winning_score}`}
        className="fc-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <FlashCalcBoard game={game} teams={gameConfig.settings.teams} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'right_flag') {
    const game = gameConfig.session.right_flag;
    return (
      <GameScreen
        {...screen}
        gameLabel="Le bon drapeau"
        detail={`Premier à ${game.winning_score}`}
        className="rf-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <RightFlagBoard game={game} teams={gameConfig.settings.teams} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'golden_family') {
    const game = gameConfig.session.golden_family;
    return (
      <GameScreen
        {...screen}
        gameLabel="Une famille en or"
        detail={`Premier à ${game.winning_score}`}
        className="gf-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <GoldenFamilyBoard game={game} teams={gameConfig.settings.teams} />
      </GameScreen>
    );
  }

  if (activeGameKey === 'forbidden_word') {
    const game = gameConfig.session.forbidden_word;
    return (
      <GameScreen
        {...screen}
        gameLabel="Le mot interdit"
        detail={game.sudden_death_round ? 'Mort subite' : '60 s par équipe'}
        className="fw-screen"
        winnerTeam={game.winner_team}
        scores={game.scores}
      >
        <ForbiddenWordBoard game={game} />
      </GameScreen>
    );
  }

  const blindtest = gameConfig.session.blindtest;
  const buzzerKeys = gameConfig.settings.buzzer_keys?.length
    ? gameConfig.settings.buzzer_keys
    : KEYBOARD_BINDINGS.slice(0, teamsOfGame.length);
  return (
    <GameScreen {...screen} gameLabel="Blindtest" className="blindtest-screen" winnerTeam={blindtest.winner_team} scores={blindtest.scores}>
      <BlindtestBoard gameConfig={gameConfig} buzzerKeys={buzzerKeys} />
    </GameScreen>
  );
}
