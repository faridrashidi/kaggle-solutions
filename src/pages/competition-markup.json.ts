import { experimental_AstroContainer as AstroContainer } from "astro/container";
import CompetitionCard from "../components/CompetitionCard.astro";
import CompetitionRow from "../components/CompetitionRow.astro";
import { competitions } from "../data/competitions";

export async function GET() {
  const container = await AstroContainer.create();
  const entries = await Promise.all(
    competitions.map(async (competition) => {
      const props = { competition };
      return [
        competition.number,
        {
          row: await container.renderToString(CompetitionRow, { props }),
          card: await container.renderToString(CompetitionCard, { props }),
        },
      ];
    }),
  );

  return Response.json(Object.fromEntries(entries));
}
