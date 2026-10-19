export class TagList {
  private tags: string[];

  constructor(tags: string[]) {
    this.tags = [...tags];
  }

  add(tag: string): void {
    this.tags.push(tag);
  }

  equals(other: TagList): boolean {
    return (
      this.tags.length === other.tags.length &&
      this.tags.every((tag, i) => tag === other.tags[i])
    );
  }
}
