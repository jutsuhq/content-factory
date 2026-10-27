// The app's icon set, one place for all of them. General icons are Phosphor duotone (MIT); index.css tints their
// second layer with the brand accent. The five sections in the sidebar have their own icons, drawn in the logo's
// language: rounded 9:16 frames, a play mark, the same stroke and the same accent layer.
import {
  ArrowLeftIcon as PhArrowLeft,
  ArrowRightIcon as PhArrowRight,
  ArrowsClockwiseIcon as ArrowsClockwise,
  ArrowSquareOutIcon as ArrowSquareOut,
  CaretDownIcon as CaretDown,
  CheckIcon as PhCheck,
  CheckCircleIcon as CheckCircle,
  CircleNotchIcon as CircleNotch,
  CopyIcon as PhCopy,
  DownloadSimpleIcon as DownloadSimple,
  EyeIcon as PhEye,
  FilmSlateIcon as FilmSlate,
  FilmStripIcon as FilmStrip,
  FloppyDiskIcon as FloppyDisk,
  FolderOpenIcon as PhFolderOpen,
  HeartIcon as PhHeart,
  ImageSquareIcon as ImageSquare,
  InfoIcon as PhInfo,
  KeyIcon as PhKey,
  LightbulbIcon as PhLightbulb,
  MicrophoneIcon as Microphone,
  MicrophoneSlashIcon as MicrophoneSlash,
  MusicNotesIcon as MusicNotes,
  PenNibIcon as PhPenNib,
  PlayIcon as PhPlay,
  QueueIcon as PhQueue,
  PlusIcon as PhPlus,
  SparkleIcon as Sparkle,
  StopIcon as Stop,
  TerminalWindowIcon as TerminalWindow,
  TranslateIcon as Translate,
  TrashIcon as Trash,
  WarningIcon as Warning,
  WifiSlashIcon as WifiSlash,
  XIcon as PhX,
  XCircleIcon as XCircle,
  type Icon as PhIcon,
} from '@phosphor-icons/react'
import type { ReactNode, SVGProps } from 'react'

type Props = { size?: number; className?: string }

const duo = (I: PhIcon, weight: 'duotone' | 'bold' = 'duotone') =>
  ({ size = 16, className }: Props) => <I size={size} weight={weight} className={className} aria-hidden />

export const ArrowLeft = duo(PhArrowLeft, 'bold')
export const ArrowRight = duo(PhArrowRight, 'bold')
export const Download = duo(DownloadSimple, 'bold')
export const Key = duo(PhKey)
export const Terminal = duo(TerminalWindow)
export const Check = duo(PhCheck, 'bold')
export const ChevronDown = duo(CaretDown, 'bold')
export const CircleCheck = duo(CheckCircle)
export const Clapperboard = duo(FilmSlate)
export const CircleX = duo(XCircle)
export const Copy = duo(PhCopy)
export const ExternalLink = duo(ArrowSquareOut)
export const Eye = duo(PhEye)
export const Film = duo(FilmStrip)
export const FolderOpen = duo(PhFolderOpen)
export const Heart = duo(PhHeart)
export const ImagePlus = duo(ImageSquare)
export const Info = duo(PhInfo)
export const Languages = duo(Translate)
export const Lightbulb = duo(PhLightbulb)
export const ListTodo = duo(PhQueue)
export const Loader2 = duo(CircleNotch, 'bold')
export const Mic = duo(Microphone)
export const MicOff = duo(MicrophoneSlash)
export const Music = duo(MusicNotes)
export const PenNib = duo(PhPenNib)
export const Play = duo(PhPlay)
export const Plus = duo(PhPlus, 'bold')
export const RefreshCw = duo(ArrowsClockwise)
export const Save = duo(FloppyDisk)
export const Sparkles = duo(Sparkle)
export const Square = duo(Stop)
export const Trash2 = duo(Trash)
export const TriangleAlert = duo(Warning)
export const WifiOff = duo(WifiSlash)
export const X = duo(PhX, 'bold')

// Own icons: 24 grid, 1.7 stroke, round joins. `duo` is the soft layer; for the open section it turns solid accent
// and the `ink` glyph on it goes dark, like the logo and the primary button.
const own = (children: ReactNode) =>
  ({ size = 16, className }: Props & SVGProps<SVGSVGElement>) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
      strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
      {children}
    </svg>
  )

/** Explore: a frame with a spark, something new to start from. */
export const NavExplore = own(
  <>
    <rect className="duo" x="5" y="3" width="11" height="18" rx="2.6" fill="currentColor" stroke="none" />
    <rect x="5" y="3" width="11" height="18" rx="2.6" />
    <path d="M18.5 4.5v4M16.5 6.5h4" />
    <path className="ink" d="M10.5 8.6l1.05 2.35 2.35 1.05-2.35 1.05-1.05 2.35-1.05-2.35-2.35-1.05 2.35-1.05z" fill="currentColor" strokeWidth={1.1} />
  </>,
)

/** My videos: the logo's stack of frames with a play mark. */
export const NavVideos = own(
  <>
    <rect x="3" y="6" width="9" height="15" rx="2.2" opacity="0.45" />
    <rect className="duo" x="8.5" y="3" width="11" height="18" rx="2.6" fill="currentColor" stroke="none" />
    <rect x="8.5" y="3" width="11" height="18" rx="2.6" />
    <path className="ink" d="M12.6 9.4v5.2l4.2-2.6z" fill="currentColor" strokeWidth={1.2} />
  </>,
)

/** Queue: jobs as bars, the first one part way done. */
export const NavQueue = own(
  <>
    <rect x="3" y="4" width="18" height="5" rx="2.5" />
    <rect className="duo" x="3" y="4" width="11" height="5" rx="2.5" fill="currentColor" stroke="none" />
    <path d="M4 14.5h16M4 19.5h10" />
  </>,
)

/** Voice: a waveform inside a capsule, the shape of the app's buttons. */
export const NavVoice = own(
  <>
    <rect className="duo" x="2.5" y="6" width="19" height="12" rx="6" fill="currentColor" stroke="none" />
    <rect x="2.5" y="6" width="19" height="12" rx="6" />
    <path className="ink" d="M7.5 10.5v3M10.5 8.8v6.4M13.5 10v4M16.5 11v2" />
  </>,
)

/** Settings: two sliders rather than the usual gear. */
export const NavSettings = own(
  <>
    <path d="M4 7.5h7M17 7.5h3M4 16.5h3M13 16.5h7" />
    <circle className="duo" cx="14" cy="7.5" r="3" fill="currentColor" stroke="none" />
    <circle cx="14" cy="7.5" r="3" />
    <circle className="duo" cx="10" cy="16.5" r="3" fill="currentColor" stroke="none" />
    <circle cx="10" cy="16.5" r="3" />
  </>,
)
