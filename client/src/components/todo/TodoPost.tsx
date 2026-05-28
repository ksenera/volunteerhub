import { ExternalLink, Clock } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "../ui/card";
import React from "react";

interface TodoPostProp {
  id: number;
  title: string;
  organization: string;
  organizationTypes: string;
  volunteerTypes: string;
  commitment: string;
  location: string;
  applicationDeadline: string;
  website: string;
  distance: number; // Distance in seconds
}

const TodoPost = ({
  title,
  organization,
  organizationTypes,
  volunteerTypes,
  commitment,
  location,
  applicationDeadline,
  website,
  distance,
}: TodoPostProp) => {
  const handleWebsiteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (website !== "TO BE DETERMINED") {
      window.open(website, "_blank", "noopener,noreferrer");
    }
  };

  const formatDistance = (seconds: number): { value: number; unit: string } => {
    const minutes = Math.ceil(seconds / 60);

    if (minutes < 60) {
      return { value: minutes, unit: "min" };
    } else if (minutes < 1440) {
      const hours = Math.ceil(minutes / 60);
      return { value: hours, unit: "hr" };
    } else {
      const days = Math.ceil(minutes / 1440);
      return { value: days, unit: "day" };
    }
  };

  const calculatePoints = (): number => {
    if (commitment.startsWith("Flexible")) {
      return 50;
    } else if (commitment.startsWith("Short term")) {
      return 100;
    } else if (commitment.startsWith("Long term")) {
      return 500;
    } else if (commitment.startsWith("Ongoing")) {
      return 2000;
    }
    return 10;
  };

  const { value, unit } = formatDistance(distance);

  const points = calculatePoints();

  return (
    <div className="inline-block max-w-[350px] m-2.5 align-top">
      <Card className="h-full flex flex-col transition-all duration-200 hover:shadow-md relative">
        <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded-lg text-xs font-medium flex items-center shadow-sm z-10">
          <Clock className="mr-1 h-3 w-3" />
          {value} {unit}
          {value !== 1 && unit === "day" ? "s" : ""}
        </div>
        <div className="absolute top-2 left-2 bg-orange-500 text-white px-2 py-1 rounded-lg text-xs font-medium flex items-center shadow-sm z-10">
          {points} points
        </div>

        <CardHeader className="pb-2 pt-6">
          <h2 className="text-xl font-bold text-primary line-clamp-2 min-h-[3.5rem]">
            {title}
          </h2>
          <p className="text-sm font-medium text-muted-foreground">
            {organization}
          </p>
        </CardHeader>
        <CardContent className="flex-grow">
          <div className="space-y-3 text-sm">
            <div className="flex gap-2 items-start">
              <span className="font-semibold min-w-[130px] shrink-0">
                Organization Types:
              </span>
              <span
                className="text-muted-foreground line-clamp-2 flex-1"
                title={organizationTypes}
              >
                {organizationTypes}
              </span>
            </div>

            <div className="flex gap-2 items-start">
              <span className="font-semibold min-w-[130px] shrink-0">
                Volunteer Types:
              </span>
              <span
                className="text-muted-foreground line-clamp-2 flex-1"
                title={volunteerTypes}
              >
                {volunteerTypes}
              </span>
            </div>

            <div className="flex gap-2 items-start">
              <span className="font-semibold min-w-[130px] shrink-0">
                Commitment:
              </span>
              <span
                className="text-muted-foreground line-clamp-2 flex-1"
                title={commitment}
              >
                {commitment}
              </span>
            </div>

            <div className="flex gap-2 items-start">
              <span className="font-semibold min-w-[130px] shrink-0">
                Location:
              </span>
              <span
                className="text-muted-foreground line-clamp-1 flex-1"
                title={location || "Remote"}
              >
                {location || "Remote"}
              </span>
            </div>

            <div className="flex gap-2 items-start">
              <span className="font-semibold min-w-[130px] shrink-0">
                Deadline:
              </span>
              <span
                className="text-muted-foreground line-clamp-1 flex-1"
                title={applicationDeadline}
              >
                {applicationDeadline}
              </span>
            </div>
          </div>
        </CardContent>
        <CardFooter className="pt-2 border-t">
          <Button
            variant="outline"
            className="w-full"
            onClick={handleWebsiteClick}
            disabled={website === "TO BE DETERMINED"}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            {website === "TO BE DETERMINED" ? "Coming Soon" : "Visit Website"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default TodoPost;
