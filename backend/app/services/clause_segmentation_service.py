import re

from app.schemas.clause import Clause


class ClauseSegmentationService:
    """
    Contract clause segmentation service.

    Design goals:
    - Preserve genuine numbered contractual clauses.
    - Preserve Schedule / Annexure / Appendix / Exhibit content.
    - Do NOT turn numbered fields inside schedules/forms into
      top-level contractual clauses.
    - Keep the original contractual wording.
    - Support OCR/extracted PDF text reasonably well.
    """

    # ================================================================
    # Patterns
    # ================================================================

    NUMBER_PATTERN = re.compile(
        r"^(\d+(?:\.\d+)*)(?:[\.\)])?\s+(.*)$"
    )

    TOP_LEVEL_NUMBER_PATTERN = re.compile(
        r"^\s*(\d+)(?:[\.\)])\s+(.+)$"
    )

    SCHEDULE_HEADING_PATTERN = re.compile(
    r"^\s*(?:"
    r"SCHEDULE(?:\s+[A-Z0-9]+)?"
    r"|ANNEXURE(?:\s+[A-Z0-9]+)?"
    r"|APPENDIX(?:\s+[A-Z0-9]+)?"
    r"|EXHIBIT(?:\s+[A-Z0-9]+)?"
    r")\s*$",
    re.IGNORECASE,
)

    NON_CLAUSE_SECTION_PATTERNS = [
    # Only match genuine standalone section headings.
    #
    # IMPORTANT:
    # Do NOT match normal contractual sentences such as:
    # "Schedule A, if repayment is not made..."
    # "Schedule A. The Borrower is aware..."
    #
    # A real schedule heading should be something like:
    # "SCHEDULE A"
    # "SCHEDULE B"
    # "ANNEXURE A"
    # "APPENDIX 1"
    # "EXHIBIT A"

    re.compile(
        r"^\s*SCHEDULE(?:\s+[A-Z0-9]+)?\s*$",
        re.IGNORECASE,
    ),

    re.compile(
        r"^\s*ANNEXURE(?:\s+[A-Z0-9]+)?\s*$",
        re.IGNORECASE,
    ),

    re.compile(
        r"^\s*APPENDIX(?:\s+[A-Z0-9]+)?\s*$",
        re.IGNORECASE,
    ),

    re.compile(
        r"^\s*EXHIBIT(?:\s+[A-Z0-9]+)?\s*$",
        re.IGNORECASE,
    ),

    # These are normally genuine standalone form/document headings.
    re.compile(
        r"^\s*APPLICATION\s+FORM\s*$",
        re.IGNORECASE,
    ),

    re.compile(
        r"^\s*SANCTION\s+LETTER\s*$",
        re.IGNORECASE,
    ),
]

    # These are table/form fields.
    #
    # They are useful inside a Schedule but must NOT become
    # independent top-level contract clauses.
    FORM_FIELD_PATTERNS = [
        re.compile(
            r"^\s*(?:amount\s+of\s+the\s+loan)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:availability\s+period)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:purpose\s+of\s+the\s+loan)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:interest)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:periodicity)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:mode\s+of\s+repayment)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:number\s+of)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:epi)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:fees\s*/\s*charges)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:prepayment\s+conditions)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:special\s+conditions)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:address\s+for\s+communication)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:name\s+of\s+the\s+branch)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?:address\s+of\s+the\s+branch)\b",
            re.IGNORECASE,
        ),
    ]

    # ================================================================
    # Public API
    # ================================================================

    @staticmethod
    def segment(text: str) -> list[Clause]:
        """
        Segment extracted contract text into searchable clauses.

        Important:
        Schedule/Annexure content is preserved as a single searchable
        block rather than being discarded.
        """

        if not text or not text.strip():
            return []

        normalized_text = ClauseSegmentationService._normalize(text)

        # ------------------------------------------------------------
        # Try normal numbered contract first.
        # ------------------------------------------------------------

        numbered_result = (
            ClauseSegmentationService
            ._split_numbered_contract_with_schedules(
                normalized_text
            )
        )

        if numbered_result is not None:
            main_blocks, schedule_blocks = numbered_result

            blocks = list(main_blocks)

            # Preserve schedules as separate searchable blocks.
            blocks.extend(schedule_blocks)

        else:
            # --------------------------------------------------------
            # Unnumbered / poorly structured contract fallback.
            # --------------------------------------------------------

            blocks = (
                ClauseSegmentationService
                ._split_into_blocks(
                    normalized_text
                )
            )

            if len(blocks) == 1:
                blocks = (
                    ClauseSegmentationService
                    ._split_into_sentences(
                        blocks[0]
                    )
                )

        clauses: list[Clause] = []

        current_sections: dict[str, str] = {}

        for block in blocks:

            clause = (
                ClauseSegmentationService
                ._parse_block(
                    block=block,
                    order=len(clauses) + 1,
                    current_sections=current_sections,
                )
            )

            if clause is None:
                continue

            clauses.append(clause)

            # Store top-level headings for subclauses.
            if (
                clause.clause_number
                and clause.title
                and "." not in clause.clause_number
            ):
                current_sections[
                    clause.clause_number
                ] = clause.title

        return clauses

    # ================================================================
    # Normalization
    # ================================================================

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalize extracted text while preserving meaningful
        line breaks.
        """

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Fix common PDF extraction artifacts.
        text = text.replace("\u00a0", " ")

        lines = []

        for line in text.split("\n"):
            cleaned = line.strip()

            # Remove page-number-only lines.
            if re.fullmatch(
                r"Page\s+\d+(?:\s+of\s+\d+)?",
                cleaned,
                re.IGNORECASE,
            ):
                continue

            if re.fullmatch(
                r"\d+\s+of\s+\d+",
                cleaned,
                re.IGNORECASE,
            ):
                continue

            lines.append(cleaned)

        normalized = "\n".join(lines)

        # Prevent excessive blank lines.
        normalized = re.sub(
            r"\n{3,}",
            "\n\n",
            normalized,
        )

        return normalized.strip()

    # ================================================================
    # Numbered contract splitting
    # ================================================================

    @classmethod
    def _split_numbered_contract_with_schedules(
        cls,
        text: str,
    ) -> tuple[list[str], list[str]] | None:
        """
        Split a numbered contract while preserving schedules.

        Example:

            1. First clause
            ...
            2. Second clause
            ...
            20. Last clause

            SCHEDULE A

            Amount of the Loan (INR)
            ...
            Interest
            ...
            Fees / Charges
            ...

        Result:

            main_blocks =
                Clause 1
                Clause 2
                ...
                Clause 20

            schedule_blocks =
                SCHEDULE A + all its contents

        Numbered fields inside Schedule A are deliberately NOT
        interpreted as top-level clauses.
        """

        lines = text.split("\n")

        if not lines:
            return None

        # ------------------------------------------------------------
        # Locate the first genuine "1." style clause.
        # ------------------------------------------------------------

        numbered_positions: list[
            tuple[int, int, str]
        ] = []

        for index, line in enumerate(lines):

            stripped = line.strip()

            match = cls.TOP_LEVEL_NUMBER_PATTERN.match(
                stripped
            )

            if not match:
                continue

            try:
                number = int(match.group(1))
            except ValueError:
                continue

            if number <= 0 or number > 200:
                continue

            numbered_positions.append(
                (
                    index,
                    number,
                    match.group(2).strip(),
                )
            )

        if len(numbered_positions) < 2:
            return None

        first_one_index = None

        for item in numbered_positions:

            if item[1] == 1:
                first_one_index = item[0]
                break

        if first_one_index is None:
            return None

        # ------------------------------------------------------------
        # Identify the main contract's numbered clauses.
        #
        # Once Schedule/Annexure begins, stop adding numbered items
        # to the main-clause sequence.
        # ------------------------------------------------------------

        valid_matches: list[
            tuple[int, int, str]
        ] = []

        schedule_start_index: int | None = None

        for item in numbered_positions:

            line_index = item[0]
            number = item[1]
            heading = item[2]

            if line_index < first_one_index:
                continue

            # Check the lines immediately before this numbered item.
            previous_context = "\n".join(
                lines[
                    max(
                        first_one_index,
                        line_index - 3,
                    ):line_index
                ]
            )

            current_line = lines[line_index].strip()

            # If the current line is actually a schedule/form heading,
            # this is not a normal numbered clause.
            if cls._is_non_clause_section_heading(
                current_line
            ):
                schedule_start_index = line_index
                break

            if cls._looks_like_form_section(
                current_line
            ):
                schedule_start_index = line_index
                break

            # If Schedule/Annexure appeared immediately before this
            # numbered item, this numbered item belongs to that
            # schedule, not the main contract.
            if cls._contains_non_clause_heading(
                previous_context
            ):
                schedule_start_index = (
                    cls._find_non_clause_section_start(
                        lines=lines,
                        start_index=max(
                            first_one_index,
                            line_index - 3,
                        ),
                    )
                )
                break

            valid_matches.append(item)

        # ------------------------------------------------------------
        # If we did not detect a schedule while scanning numbered
        # positions, explicitly find the first schedule after clause 1.
        # ------------------------------------------------------------

        explicit_schedule_start = (
            cls._find_non_clause_section_start(
                lines=lines,
                start_index=first_one_index,
            )
        )

        if (
            explicit_schedule_start is not None
            and (
                schedule_start_index is None
                or explicit_schedule_start
                < schedule_start_index
            )
        ):
            schedule_start_index = (
                explicit_schedule_start
            )

        # ------------------------------------------------------------
        # Need at least two actual main clauses.
        # ------------------------------------------------------------

        if len(valid_matches) < 2:
            return None

        # ------------------------------------------------------------
        # Validate numbering.
        # ------------------------------------------------------------

        numbers = [
            item[1]
            for item in valid_matches
        ]

        if numbers[0] != 1:
            return None

        sequential_count = 0
        expected = 1

        for number in numbers:

            if number == expected:
                sequential_count += 1
                expected += 1

            elif number > expected:

                # Allow a small OCR/missing-clause gap.
                if number - expected <= 2:
                    expected = number + 1
                    sequential_count += 1
                else:
                    break

            else:
                # Duplicate or backwards numbering is suspicious.
                continue

        if sequential_count < 2:
            return None

        # ------------------------------------------------------------
        # Build main clause blocks.
        # ------------------------------------------------------------

        main_blocks: list[str] = []

        for index, item in enumerate(valid_matches):

            line_index = item[0]

            if index + 1 < len(valid_matches):

                next_line_index = (
                    valid_matches[index + 1][0]
                )

                block_lines = lines[
                    line_index:next_line_index
                ]

            else:

                # Last main clause ends before Schedule/Annexure.
                if schedule_start_index is not None:
                    end_index = schedule_start_index
                else:
                    end_index = len(lines)

                block_lines = lines[
                    line_index:end_index
                ]

            block = "\n".join(
                block_lines
            ).strip()

            if block:
                main_blocks.append(block)

        # ------------------------------------------------------------
        # Build schedule blocks.
        #
        # Keep each schedule as ONE block.
        #
        # This is important because Schedule A can contain:
        #
        # Amount of the Loan
        # Interest
        # EPI
        # Fees
        # Prepayment conditions
        # Special conditions
        #
        # and those fields must remain searchable together.
        # ------------------------------------------------------------

        schedule_blocks: list[str] = []

        if schedule_start_index is not None:

            # Find subsequent Schedule/Annexure headings.
            section_starts = [
                schedule_start_index
            ]

            for index in range(
                schedule_start_index + 1,
                len(lines),
            ):
                line = lines[index].strip()

                if cls._is_non_clause_section_heading(
                    line
                ):
                    section_starts.append(index)

            # Remove duplicates and sort.
            section_starts = sorted(
                set(section_starts)
            )

            for index, start in enumerate(
                section_starts
            ):

                if index + 1 < len(section_starts):
                    end = section_starts[index + 1]
                else:
                    end = len(lines)

                block = "\n".join(
                    lines[start:end]
                ).strip()

                if not block:
                    continue

                # Ignore isolated form fields if they somehow appear
                # without a schedule heading.
                if cls._looks_like_form_section(
                    block.split("\n")[0].strip()
                ):
                    continue

                schedule_blocks.append(block)

        return (
            main_blocks,
            schedule_blocks,
        )

    # ================================================================
    # Schedule / Annexure / Form detection
    # ================================================================

    @classmethod
    def _is_non_clause_section_heading(
        cls,
        line: str,
    ) -> bool:

        if not line:
            return False

        for pattern in cls.NON_CLAUSE_SECTION_PATTERNS:

            if pattern.search(line):
                return True

        return False

    @classmethod
    def _contains_non_clause_heading(
        cls,
        text: str,
    ) -> bool:

        if not text:
            return False

        for line in text.split("\n"):

            if cls._is_non_clause_section_heading(
                line.strip()
            ):
                return True

        return False

    @classmethod
    def _find_non_clause_section_start(
        cls,
        lines: list[str],
        start_index: int,
    ) -> int | None:
        """
        Find the first Schedule/Annexure/Appendix/Exhibit/Form
        heading after start_index.
        """

        for index in range(
            start_index,
            len(lines),
        ):

            line = lines[index].strip()

            if cls._is_non_clause_section_heading(
                line
            ):
                return index

        return None

    @classmethod
    def _looks_like_form_section(
        cls,
        line: str,
    ) -> bool:

        if not line:
            return False

        for pattern in cls.FORM_FIELD_PATTERNS:

            if pattern.search(line):
                return True

        return False

    # ================================================================
    # Generic block splitting
    # ================================================================

    @staticmethod
    def _split_into_blocks(
        text: str,
    ) -> list[str]:
        """
        Split unnumbered contract text using blank lines.
        """

        raw_blocks = re.split(
            r"\n\s*\n",
            text,
        )

        blocks: list[str] = []

        for raw_block in raw_blocks:

            block = raw_block.strip()

            if not block:
                continue

            # OCR bullet/list items belong to the previous block.
            if (
                re.match(
                    r"^[-*•â€¢°¢]\s+",
                    block,
                )
                and blocks
            ):
                blocks[-1] = (
                    f"{blocks[-1]}\n{block}"
                )

            else:
                blocks.append(block)

        return blocks

    # ================================================================
    # Flat contract fallback
    # ================================================================

    @classmethod
    def _split_flat_contract(
        cls,
        text: str,
    ) -> list[str]:
        """
        Fallback for contracts where numbered headings occur
        without useful paragraph structure.
        """

        text = text.strip()

        if not text:
            return []

        parts = re.split(
            r"(?m)(?=^\d+(?:\.\d+)*[\.)]?\s+)",
            text,
        )

        blocks = [
            part.strip()
            for part in parts
            if part.strip()
        ]

        if len(blocks) <= 1:
            return cls._split_into_sentences(
                text
            )

        return blocks

    # ================================================================
    # Heading merging
    # ================================================================

    @classmethod
    def _merge_numbered_headings(
        cls,
        blocks: list[str],
    ) -> list[str]:
        """
        Merge numbered headings with the following block.

        Kept for compatibility with existing code/tests.
        """

        merged: list[str] = []

        index = 0

        while index < len(blocks):

            block = blocks[index]

            lines = block.split("\n")

            first_line = lines[0].strip()

            match = cls.NUMBER_PATTERN.match(
                first_line
            )

            if (
                match
                and "." not in match.group(1)
                and len(lines) == 1
                and index + 1 < len(blocks)
            ):

                number = match.group(1)

                heading = match.group(2).strip()

                if (
                    len(heading) <= 100
                    and any(
                        char.isalpha()
                        for char in heading
                    )
                ):

                    next_block = (
                        blocks[index + 1].strip()
                    )

                    merged.append(
                        f"{number}. {heading}\n"
                        f"{next_block}"
                    )

                    index += 2
                    continue

            merged.append(block)

            index += 1

        return merged

    # ================================================================
    # Sentence splitting
    # ================================================================

    @staticmethod
    def _split_into_sentences(
        text: str,
    ) -> list[str]:
        """
        Fallback for unstructured text.
        """

        sentences = re.split(
            r"(?<=[.!?])\s+(?=[A-Z])",
            text.strip(),
        )

        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    # ================================================================
    # Parse block
    # ================================================================

    @classmethod
    def _parse_block(
        cls,
        block: str,
        order: int,
        current_sections: dict[str, str],
    ) -> Clause | None:

        if not block or not block.strip():
            return None

        lines = block.split("\n")

        if not lines:
            return None

        first_line = lines[0].strip()

        # ------------------------------------------------------------
        # Schedule / Annexure block
        # ------------------------------------------------------------

        if cls._is_non_clause_section_heading(
            first_line
        ):

            # Example:
            #
            # SCHEDULE A
            # Amount of the Loan (INR) ...
            # Interest ...
            #
            # Keep ALL content together.
            title = first_line

            clause_text = (
                "\n".join(
                    lines[1:]
                ).strip()
            )

            if not clause_text:
                return None

            return Clause(
                clause_id=f"clause-{order}",
                title=title,
                text=clause_text,
                order=order,
                character_count=len(clause_text),
                clause_number=None,
                parent_clause=None,
            )

        # ------------------------------------------------------------
        # Numbered clause
        # ------------------------------------------------------------

        match = cls.NUMBER_PATTERN.match(
            first_line
        )

        if match:

            clause_number = match.group(1)

            remainder = match.group(2).strip()

            parent_clause = cls._get_parent(
                clause_number
            )

            title = (
                current_sections.get(
                    parent_clause
                )
                if parent_clause
                else None
            )

            # --------------------------------------------------------
            # TOP-LEVEL NUMBERED CLAUSE
            # --------------------------------------------------------

            if "." not in clause_number:

                # Determine whether the first line is a heading.
                #
                # "2. PAYMENT TERMS"
                # -> heading
                #
                # "2. USFB agrees to grant..."
                # -> contractual text
                is_heading = (
                    len(remainder) <= 100
                    and any(
                        char.isalpha()
                        for char in remainder
                    )
                    and not re.search(
                        r"[.!?]$",
                        remainder,
                    )
                    and not re.search(
                        r"\b(?:shall|agrees|agreed|"
                        r"undertakes|confirms|represents|"
                        r"declares|recognizes|recognises|"
                        r"hereby|will|must|may|"
                        r"is|are|has|have)\b",
                        remainder,
                        re.IGNORECASE,
                    )
                )

                # ----------------------------------------------------
                # Real heading
                # ----------------------------------------------------

                if is_heading and len(lines) >= 2:

                    title = remainder

                    clause_text = (
                        "\n".join(
                            lines[1:]
                        ).strip()
                    )

                    if not clause_text:
                        return None

                    return Clause(
                        clause_id=f"clause-{order}",
                        title=title,
                        text=clause_text,
                        order=order,
                        character_count=len(clause_text),
                        clause_number=clause_number,
                        parent_clause=None,
                    )

                # ----------------------------------------------------
                # No separate heading.
                #
                # VERY IMPORTANT:
                # Keep the first numbered line.
                #
                # For your document:
                #
                # 2. USFB agrees to grant to the Borrower...
                #
                # This entire sentence belongs to Clause 2.
                # ----------------------------------------------------

                clause_text = (
                    "\n".join(lines).strip()
                )

                if not clause_text:
                    return None

                return Clause(
                    clause_id=f"clause-{order}",
                    title=None,
                    text=clause_text,
                    order=order,
                    character_count=len(clause_text),
                    clause_number=clause_number,
                    parent_clause=None,
                )

            # --------------------------------------------------------
            # SUB-CLAUSE
            # --------------------------------------------------------

            if len(lines) == 1:
                clause_text = remainder

            else:
                clause_text = (
                    "\n".join(
                        [remainder] + lines[1:]
                    ).strip()
                )

            if not clause_text:
                return None

            return Clause(
                clause_id=f"clause-{order}",
                title=title,
                text=clause_text,
                order=order,
                character_count=len(clause_text),
                clause_number=clause_number,
                parent_clause=parent_clause,
            )

        # ------------------------------------------------------------
        # Ignore standalone uppercase document titles.
        # ------------------------------------------------------------

        if (
            len(block) <= 100
            and block.upper() == block
            and any(
                char.isalpha()
                for char in block
            )
        ):
            return None

        # ------------------------------------------------------------
        # Unnumbered content
        # ------------------------------------------------------------

        return Clause(
            clause_id=f"clause-{order}",
            title=None,
            text=block,
            order=order,
            character_count=len(block),
            clause_number=None,
            parent_clause=None,
        )

    # ================================================================
    # Parent clause
    # ================================================================

    @staticmethod
    def _get_parent(
        clause_number: str,
    ) -> str | None:

        parts = clause_number.split(".")

        if len(parts) <= 1:
            return None

        return ".".join(
            parts[:-1]
        )